import os
import sys
import math
import json
import psycopg2
import psycopg2.extras
from algoliasearch.search_client import SearchClient
from Lib.CLI import *
from dotenv import load_dotenv


def algolia_sync(arguments):
    environment = 'production'
    if len(arguments) >= 2 and arguments[1] == '--local':
        load_dotenv()
        environment = 'local'

    info("Connecting to DB")
    db = None
    try:
        if not os.environ['DATABASE_URL'] or environment == 'local':
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

    except Exception as e:
        error("Unable to connect to database.")
        error(e)
        return False

    client = SearchClient.create(os.getenv('ALGOLIA_APPLICATION_ID'),
                                 os.getenv('ALGOLIA_ADMIN_KEY'))

    index_name = os.getenv('ALGOLIA_INDEX')
    temp_index_name = f'{index_name}_temp'

    index = client.init_index(index_name)
    temp_index = client.init_index(temp_index_name)


    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    per_page = 25
    count = 0

    AWS_MEDIA_BUCKET_NAME = os.environ.get("AWS_MEDIA_BUCKET_NAME", '')

    # Get product count
    try:
        cursor.execute('SELECT COUNT(*) AS count from product_product')
        result = cursor.fetchone()
        count = result['count']
        comment(f'{count} product{"s" if count != 1 else ""} found.')
    except Exception as e:
        error("Can't get product count.")
        error(e)
        return False

    pages = math.ceil(count / per_page)
    comment(f'Page count: {pages}')
    print("")

    for page in range(pages):
        comment(f'Syncing page {page + 1}')
        try:
            cursor.execute(f"""
                        SELECT p.id, p.name, p.slug, p.description_json, p.in_stock,
                        pc.name AS category_name, pt.name AS product_type, pi.image,
					    (SELECT MIN(price_amount) FROM product_productvariant WHERE product_productvariant.product_id = p.id) AS price
                        FROM product_product p
                        LEFT JOIN product_category pc ON pc.id = p.category_id
                        LEFT JOIN product_producttype pt ON pt.id = p.product_type_id
                        LEFT JOIN product_productimage pi ON pi.product_id = p.id AND pi.id = (SELECT MIN(id) FROM product_productimage WHERE product_id = p.id)
                        WHERE p.is_published = 'TRUE'
                        ORDER BY id ASC
                        LIMIT {per_page}
                        OFFSET {per_page * page}
                    """)

            results = cursor.fetchall()
            objects = []
            if results is not None:
                for result in results:

                    # Parse the description
                    description = ''
                    dj = result['description_json']
                    if dj and type(dj) is dict and 'blocks' in dj.keys():
                        description = ' '.join(b['text'] for b in dj['blocks'])

                    # Add algolia object
                    object = {
                        'objectID': result['id'],
                        'slug': result['slug'],
                        'name': result['name'],
                        'image': f'https://{AWS_MEDIA_BUCKET_NAME}.s3.amazonaws.com/{result["image"]}',
                        'category': result['category_name'],
                        'product_type': result['product_type'],
                        'description': description,
                        'price': '{:.2f}'.format(float(result['price'])) if result['price'] else '',
                        'in_stock': result['in_stock']
                    }

                    objects.append(object)

                temp_index.save_objects(objects)

        except Exception as e:
            error(f'Error syncing.')
            error(e)
            return False

    comment("Copying index settings...")
    client.copy_synonyms(index_name, temp_index_name)
    client.copy_settings(index_name, temp_index_name)

    comment("Moving temp index to production...")
    client.move_index(temp_index_name, index_name)
    print("")
    info("Done")


if __name__ == '__main__':
    algolia_sync(sys.argv)
