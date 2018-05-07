"""Instagram API
"""

import os
import logging
import time
import json
from dotenv import load_dotenv, find_dotenv
import requests

load_dotenv(find_dotenv())

BASE_URL = os.getenv("BASE_URL")
SECONDARY_BASE_URL = os.getenv("SECONDARY_BASE_URL")

class Instagram:
    """Instagram API
    """

    def __init__(self, debug=False):

        if debug:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

        self.logger = logging.getLogger(__name__)

        self.session = requests.Session()
        # self.session.headers.update({})

        self.debug = debug
        self.LastJson = None

    def _send_request(self, endpoint, method='GET', base_url=BASE_URL, params=None, data=None): #pylint: disable=R0913
        """send request to specific endpoint
        
        Arguments:\n
            endpoint {str} -- endpoint to send the request\n
            method {str} -- method of the request\n
            params {Dict} -- parameter dictionary to send as query string (default: {None})\n
            post {str} -- method of the request (default: {None})\n
        
        Returns:
            bool -- represents whether the request was successful or not
        """

        while True:
            try:
                if method.upper() == 'POST':
                    response = self.session.post(base_url + endpoint, data=data, json=params)
                elif method.upper() == 'GET':
                    response = self.session.get(base_url + endpoint, params=params)
                else:
                    self.logger.exception(f'sent a request with wrong method {method}')
                    return False
                break
            except Exception as e:
                self.logger.exception(f'Except on SendRequest (wait 60 sec and resend): {str(e)}')
                time.sleep(60)

        if response.status_code == 200:
            try:
                self.LastJson = json.loads(response.text)
                return True
            except Exception as e:
                self.logger.error(f"response parsing error: {str(e)}")
                return False

        self.logger.error(f"Request returns {response.status_code} error!")
        self.logger.error(f"error response: {response.text}")
        return False

    def search(self, query, context='hashtag'):
        """search user, hashtag or locations in Instagram
        
        Arguments:
            query {str} -- query to search
        
        Keyword Arguments:
            context {str} -- context of the search (default: {'blended'})
        """

        self.logger.info(f"called search with {query}")
        return self._send_request(f'web/search/topsearch/?query={query}&context={context}')

    def get_media_feed_by_hashtag(self, hashtag):
        """get post feed related with specific hashtag
        
        Arguments:
            hashtag {str} -- hashtag to search
        """

        self.logger.info(f"called get_media_feed_by_hashtag with {hashtag}")
        return self._send_request(f'explore/tags/{hashtag}/?__a=1')

    def get_user(self, user_id):
        """get the user specified by user_id
        
        Arguments:
            user_id {str} -- user id
        """

        self.logger.info(f"called get_user with {user_id}")
        return self._send_request(f'users/{user_id}/info', base_url=SECONDARY_BASE_URL)

    def get_media_feed_by_user(self, username):
        """get media feed posted by the username
        
        Arguments:
            username {str} -- username
        """

        self.logger.info(f"called get_media_feed_by_user with {username}")
        return self._send_request(f'{username}/?__a=1')
