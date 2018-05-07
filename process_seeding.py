"""process seeding list
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

DB_HOST = os.getenv('DB_HOST')
DB_USERNAME = os.getenv('DB_USERNAME')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_PORT = os.getenv('DB_PORT')

mongo_client = MongoClient(f'mongodb://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}')
aggregation = mongo_client.aggregation

seeding_list_path = os.path.join(os.path.dirname(__file__), 'seeding_list.txt')
try:
    with open(seeding_list_path) as file:
        keywords = []
        for line in [line.rstrip() for line in file if line != '\n']:
            keywords += [keyword.strip().lower().replace(' ', '').replace("'s", "s") for keyword in line.split('>')[-1].split(',')]
        keywords = sorted(list(set(keywords)))

    aggregation.keywords.insert_many([{'keyword': keyword} for keyword in keywords])

except Exception as e:
    print(e)
    exit()
