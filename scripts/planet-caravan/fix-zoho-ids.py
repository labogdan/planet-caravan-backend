import json
import mimetypes
import urllib

import requests
import os
import sys
from dotenv import load_dotenv
from Lib.CLI import *
from Lib.helpers import handleize, description_block
from Lib.Saleor.Product import Product
from Lib.Saleor.Variant import Variant
from Lib.Saleor.ProductType import ProductType
from Lib.Saleor.ProductAttribute import ProductAttribute
from Lib.Saleor.ProductAttributeValue import ProductAttributeValue
from Lib.Saleor.Category import Category
from Lib.Saleor.ProductCollection import ProductCollection
import psycopg2
from psycopg2.extras import DictCursor
from pprint import pprint
import boto3
import pickle

oauth_token = None

# Global variable
cursor = None
db = None

def db_connect(environment='local'):
    info("Connecting to DB")
    global db

    try:
        if environment == 'local':
            # Local dev
            db_name = os.getenv('DB_NAME')
            db_user = os.getenv('DB_USER')
            db_host = os.getenv('DB_HOST')
            db_pass = os.getenv('DB_PASS')

            db = psycopg2.connect(
                f"dbname='{db_name}' user='{db_user}' host='{db_host}' password='{db_pass}'")
        else:
            # Heroku Production
            db_host = os.environ['DATABASE_URL']
            db = psycopg2.connect(db_host, sslmode='require')

        db.autocommit = True
        return db
    except Exception as e:
        error("Unable to connect to database.")
        error(e)
        return False


def get_oauth():
    global oauth_token

    oauth_url = 'https://accounts.zoho.com/oauth/v2/token'

    params = {
        'client_id': os.getenv('ZOHO_CLIENT_ID'),
        'client_secret': os.getenv('ZOHO_CLIENT_SECRET'),
        'refresh_token': os.getenv('ZOHO_REFRESH_TOKEN'),
        'grant_type': 'refresh_token'
    }

    response = requests.post(url=oauth_url, params=params)

    if response is not None:
        oauth_token = response.json()['access_token']
        return True

    return False


def fix_ids(arguments):
    global oauth_token
    global cursor
    environment = 'production'
    if len(arguments) >= 1 and arguments[0] == '--local':
        del arguments[0]
        environment = 'local'
        load_dotenv()

    db = db_connect(environment)
    if not db:
        error('Cannot connect to database.')
        return False

    cursor = db.cursor()

    if not get_oauth():
        error("Could not retrieve updated access token.")

    url = 'https://www.zohoapis.com/crm/v2/Products'

    headers = {
        'Authorization': f'Zoho-oauthtoken {oauth_token}',
        # 'If-Modified-Since': '2020-03-19T17:59:50+05:30'
    }

    parameters = {
        'page': 1,
        'per_page': 200,
    }

    keep_going = True

    # Clear everything out initially
    cursor.execute("""
    UPDATE product_product SET private_metadata = '{}'
    """)

    while keep_going:

        info(f'Fetching page {parameters["page"]}')
        response = requests.get(url=url, headers=headers, params=parameters)

        if response is not None:
            data = response.json()
            response_info = data['info']

            products = data['data']

            for product in products:
                sku = product['SKU']
                zoho_id = product['id']

                if sku:
                    sku = str(sku).strip("'")
                    comment(f"{product['Product_Name']}: {sku}")

                    cursor.execute("""
                    UPDATE product_product
                    SET private_metadata = %s
                    FROM product_productvariant
                    WHERE product_product.id = product_productvariant.product_id
                        AND LOWER(product_productvariant.sku) = %s
                    """, (json.dumps({'ZOHO_ID': zoho_id}), sku))

            parameters['page'] += 1
            keep_going = response_info['more_records']
        else:
            keep_going = False


if __name__ == '__main__':
    fix_ids(sys.argv[1:])
    print('')
    warning('Done.')
