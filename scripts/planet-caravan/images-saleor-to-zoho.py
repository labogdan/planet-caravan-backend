import sys
import urllib.request
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
import json

oauth_token = None

# Global variable
cursor = None
db = None


def move_images(arguments):
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

    cursor = db.cursor(cursor_factory=DictCursor)

    if not get_oauth():
        error("Could not retrieve updated access token.")

    # Upload stuff
    warning("Doing upload")

    cursor.execute("""
        SELECT id, name, private_metadata->>'ZOHO_ID' AS zoho_id
        FROM product_product
        WHERE private_metadata->>'ZOHO_ID' IS NOT NULL
    """)

    products = cursor.fetchall()
    continuing = False
    for p in products:
        zoho_product_id = p['zoho_id']

        comment('')
        comment('================================')
        comment(f"{p['name']}: {zoho_product_id}")


        if zoho_product_id == '3980137000008779936':
            info('Found product, continuing')
            continuing = True

        if not continuing:
            continue


        cursor.execute("""
            SELECT image
            FROM product_productimage
            WHERE product_id = %s
        """, (p['id'],))

        db_images = cursor.fetchall()
        images = []
        for image in db_images:
            full_url = f'https://planet-caravan.s3.amazonaws.com/{image["image"]}'
            images.append({
                'url': full_url,
                'filename': os.path.basename(full_url),
                'id': None
            })

        if len(images) == 0:
            warning('No images, continuing.')
            continue

        headers = {
            'Authorization': f'Zoho-oauthtoken {oauth_token}'
        }

        for image in images:
            try:
                request_body = {
                    'file': (image['filename'], urllib.request.urlopen(image['url']))
                }

                resp = requests.post(
                    url=f'https://www.zohoapis.com/crm/v2/files',
                    headers=headers,
                    files=request_body
                ).json()
                image['id'] = resp['data'][0]['details']['id']
            except:
                pass


        # Update the product
        update_url = f'https://www.zohoapis.com/crm/v2/Products'
        update_data = {
            "data": [
                {
                    "id": zoho_product_id,
                    "Product_Photos": [img['id'] for img in images if
                                       img['id'] is not None]
                }
            ]
        }
        warning('UPDATE DATA')
        pprint(update_data)
        updated = requests.put(url=update_url,
                               headers=headers,
                               data=json.dumps(update_data).encode('utf-8'))

        warning('FINAL RESPONSE')
        pprint(updated.json())
    info("Done")

def db_connect(environment='local'):
    global db
    info("Connecting to DB")

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
    info("Getting OAuth")

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


if __name__ == '__main__':
    move_images(sys.argv[1:])
    print('')
    warning('Done.')
