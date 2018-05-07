"""
Instagram crawler module
"""

from instagram_crawler import InstagramCrawler

crawler = InstagramCrawler(debug=True)
crawler.start()

print('>>> Done!')
