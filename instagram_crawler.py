"""Instagram Crawler
"""

import os
import logging
from pymongo import MongoClient
from dotenv import load_dotenv, find_dotenv
from instagram_api import Instagram

load_dotenv(find_dotenv())

class InstagramCrawler:
    """Instagram Crawler class
    """

    def __init__(self, debug=False):
        if debug:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

        self.logger = logging.getLogger(__name__)
        self.debug = debug

        self.instagram = Instagram(True)
        self.logger.info('Instagram Crawler instance created!')

        self.keyword = '' # keywork the crawler is searching for currently

        DB_HOST = os.getenv('DB_HOST')
        DB_USERNAME = os.getenv('DB_USERNAME')
        DB_PASSWORD = os.getenv('DB_PASSWORD')
        DB_PORT = os.getenv('DB_PORT')

        self.mongo_client = MongoClient(f'mongodb://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}')

    def _search_hashtags(self, keyword):
        """search all available hashtags including specified keyword
        
        Arguments:
            keyword {str} -- keyword to search hashtags
        
        Returns:
            List -- list of hashtags or None when search fails
        """

        self.keyword = keyword.lower() # store last searched keyword
        self.logger.info(f'called search_hashtags with {keyword}')
        if not self.instagram.search(keyword): # todo: load more of hashtags
            return None

        result = self.instagram.LastJson

        hashtags = [hashtag['hashtag']['name'] for hashtag in result['hashtags']]

        return hashtags

    def _get_owners_of_hashtags(self, hashtags):
        """get list of owner id related with
        
        Arguments:
            hashtags {List} -- list of hashtags
        
        Returns:
            List -- list of owner id
        """

        self.logger.info(f"called get_owners_of_hashtags")

        owner_id_list = []
        for hashtag in hashtags: # extract owner id list related with each hashtag
            if not self.instagram.get_media_feed_by_hashtag(hashtag):
                continue

            result = self.instagram.LastJson
            owner_id_list += [post['node']['owner']['id'] for post in result['graphql']['hashtag']['edge_hashtag_to_top_posts']['edges']]

            if self.debug:
                break
        
        return owner_id_list

    def _set_engagement_rate(self, user):
        """set engagement_rate field into user
        
        Arguments:
            user {Dict} -- full user profile dictionary before pre-processing to calculate engagement_rate
        
        Returns:
            float -- engagement_rate
        """

        self.logger.info(f"called set_engagement_rate")

        follower_count = user['followed_by']['count']

        total_engagement_rate = 0
        average_engagement_rate = 0
        post_count = 10
        for i in range(0, 10):
            if i >= len(user['media']['nodes']):
                post_count = i
                break
            post = user['media']['nodes'][i]
            total_engagement_rate += (post['comments']['count'] + post['likes']['count'] + (post['video_views'] if post['is_video'] else 0)) / follower_count

        average_engagement_rate = total_engagement_rate / post_count
        return round(average_engagement_rate, 2)

    def _get_user(self, user_id):
        """get compatible user for socian
        
        Arguments:
            user_id {str} -- Instagram user id
        
        Returns:
            Dict -- socian compatible user dictionary
        """

        self.logger.info(f"called get_user with {user_id}")

        if not self.instagram.get_user(user_id):
            return None

        result = self.instagram.LastJson
        username = result['user']['username']

        if not self.instagram.get_media_feed_by_user(username):
            return None

        return self._process_user(self.instagram.LastJson['user'])

    def _process_user(self, user):
        """pre-process user data before stores it to database for schema matching
        
        Arguments:
            user {Dict} -- user dictionary to process
        
        Returns:
            Dict -- processed user dictionary
        """

        self.logger.info(f"called process_user")

        engagement_rate = self._set_engagement_rate(user)

        processed_user = {
            "username": user["username"],
            "platform_id": user["id"],
            "platform": "instagram",
            "display_name": user["full_name"],
            "followers": user["followed_by"]["count"],
            "following": user["follows"]["count"],
            "profile_picture": user["profile_pic_url_hd"],
            "profile_picture_thumbnail": user["profile_pic_url"],
            "bio": user["biography"],
            "engagement_rate": engagement_rate,
            "location_lat": 0,
            "location_long": 0,
            "profile_score": "TBD",
            "post_history": []
        }

        posts = user['media']['nodes']
        if not isinstance(posts, list):
            return processed_user
        
        recent_posts = []
        for i, post in enumerate(posts):
            if i >= 3:
                break
            recent_posts.append(post)

        processed_user['post_history'] = recent_posts

        return processed_user

    def _store_users(self, users):
        """store user data list to database
        
        Arguments:
            users {List} -- user list
        """

        self.logger.info(f"called store_users")

        aggregation = self.mongo_client.aggregation

        for user in users:
            try:
                old_user = aggregation.profiles.find_one({'username': user['username']})
                if old_user is not None:
                    # add keyword to existing keywords field
                    try:
                        keywords = old_user['keywords']
                        if self.keyword not in keywords:
                            keywords.append(self.keyword)
                    except KeyError:
                        keywords = [self.keyword]
                else:
                    keywords = [self.keyword]
                user['keywords'] = keywords
                aggregation.profiles.find_one_and_replace({'username': user['username']}, user, None, None, True)
            except Exception as e:
                self.logger.exception(f"db error: {str(e)}")
                continue

    def start(self):
        """start crawler with keyword list
        """

        # get keywords to scrap
        aggregation = self.mongo_client.aggregation
        keywords = [keyword['keyword'] for keyword in list(aggregation.keywords.find(projection={'_id': False}))]

        # scrapping profiles through keywords
        for keyword in keywords:
            hashtags = self._search_hashtags(keyword)
            if hashtags is None:
                continue
            
            owners = self._get_owners_of_hashtags(hashtags)
            users = [self._get_user(user_id) for user_id in owners]
            self._store_users(users)

            if self.debug:
                break
