import os
import sys
import json
import mimetypes
import urllib
import requests

import django

sys.path.append(os.path.abspath('.'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "saleor.settings")
try:
    django.setup()
except:
    pass
from django.core.cache import cache


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
from datetime import datetime, timedelta




oauth_token = None

# Global variable
cursor = None
db = None
environment = 'local'

def db_connect(env='production'):
    info("Connecting to DB")
    global db
    global environment

    environment = env

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


def handle_raw_product(raw_product: dict = None, config: dict = None):
    global cursor

    if not config:
        config = {
            'force_images': False
        }

    print('======================================')
    warning(f'handle_raw_product(): {raw_product["Product_Name"]}')

    # Product
    product = Product()
    product.name = raw_product['Product_Name'].split('|')[0].strip()
    product.slug = handleize(raw_product['Product_Name'])
    product.description = str(raw_product['Description'])
    product.description_json = description_block(raw_product['Description'])
    product.metadata = '{}'
    product.private_metadata = json.dumps({
        'ZOHO_ID': raw_product['id']
    })

    # Variant
    variant = Variant()
    variant.name = str(raw_product['Product_Name'])
    variant.sku = str(raw_product['SKU']).strip("'")

    if not variant.sku:
        error("No SKU, skipping.")
        return False

    variant.cost_price_amount = raw_product['Cost']
    variant.weight = 0
    variant.price_amount = raw_product['Unit_Price']

    product.variants.append(variant)

    # Product type
    pt = ProductType()
    pt.type = raw_product['Category']
    pt.slug = handleize(raw_product['Category'])

    # Category
    if 'Department' not in raw_product.keys() or raw_product['Department'] is None:
        error(f'Product {product.name} has no Department')
        return

    parent_category = Category(raw_product['Department'])

    if 'Category' not in raw_product.keys() or raw_product['Category'] is None:
        error(f'Product {product.name} has no Category')
        return

    child_category = Category(raw_product['Category'])
    child_category.level = 1
    parent_category.children.append(child_category)

    product.category = parent_category

    # Attributes
    for i in range(1, 7):
        name_key = f'Attribute_Name_{i}'
        value_key = f'Attribute_Value_{i}'

        if (name_key in raw_product.keys() and value_key in raw_product.keys()
                and raw_product[name_key] and raw_product[value_key]):
            product_attribute = ProductAttribute(raw_product[name_key],
                                                 [ProductAttributeValue(
                                                     raw_product[value_key])])
            pt.add_attribute(product_attribute)
    product.type = pt

    # Collections
    if 'Collection' in raw_product.keys() and type(raw_product['Collection']) is str:
        for collection_name in raw_product['Collection'].split(','):
            collection_name = collection_name.strip()
            collection = ProductCollection()
            collection.name = collection_name
            collection.slug = handleize(collection_name)

            product.collections.append(collection)

    create_or_update_data(product)

    # Images
    handle_images(product, raw_product, config['force_images'])


def create_or_update_data(product: Product = None):
    global cursor
    info(f'create_or_update_data(): {product.name} | {product.variants[0].sku}')
    product.type = handle_product_type(product.type)
    comment(f'Product type ID: {product.type.id}')

    product.category = handle_product_category(product.category)
    comment(f'Product category ID: {product.category.children[0].id}')

    product.collections = handle_product_collection(product.collections)

    # Create the product, matched by SKU
    cursor.execute("""
        SELECT p.id
        FROM product_productvariant pv
        LEFT JOIN product_product p ON pv.product_id = p.id
        WHERE pv.sku = %s
    """, (product.variants[0].sku,))

    product_result = cursor.fetchone()

    if product_result:
        product.id = product_result[0]
        cursor.execute("""
            UPDATE product_product
            SET id = product_product.id, name = %s,
                description = %s, description_json = %s, product_type_id = %s,
                category_id = %s, private_metadata = %s, updated_at = NOW()
            WHERE id = %s
           """,
           (
               # UPDATE clause
               product.name, product.description, product.description_json,
               product.type.id, product.category.children[0].id,
               product.private_metadata,
               product.id
       ))
    else:
        cursor.execute("""
               INSERT INTO product_product
               (name, description, description_json, product_type_id, category_id,
               is_published, charge_taxes, currency, slug, visible_in_listings, metadata,
               private_metadata, in_stock, publication_date, updated_at, available_for_purchase)
               VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW())
               ON CONFLICT (slug) DO UPDATE
                SET id = product_product.id, name = %s,
                    description = %s, description_json = %s, product_type_id = %s,
                    category_id = %s, private_metadata = %s, updated_at = NOW()
               RETURNING id
               """,
           (
                # INSERT clause
                product.name, product.description, product.description_json,
                product.type.id, product.category.children[0].id, product.is_published, product.charge_taxes,
                product.currency, product.slug, product.visible_in_listings,
                product.metadata, product.private_metadata, False,

                # UPDATE clause
                product.name, product.description, product.description_json,
                product.type.id, product.category.children[0].id, product.private_metadata
            ))

        product.id = cursor.fetchone()[0]

    info(f'Product ID: {product.id}')

    # Add Attributes
    for i, attribute in enumerate(product.type.attributes):
        cursor.execute("""
            INSERT INTO product_assignedproductattribute(product_id, assignment_id)
            VALUES(%s, %s)
            ON CONFLICT (product_id, assignment_id) DO UPDATE
                SET id = product_assignedproductattribute.id
            RETURNING id
        """,
        (product.id, attribute.assignment_id))
        apa_id = cursor.fetchone()[0]

        # Clear out prior attribute
        cursor.execute("""
            DELETE FROM product_assignedproductattribute_values
            WHERE assignedproductattribute_id = %s
        """, (apa_id,))

        # Create the new value
        cursor.execute("""
                INSERT INTO product_assignedproductattribute_values
                    (assignedproductattribute_id, attributevalue_id)
                VALUES(%s, %s)
                ON CONFLICT (assignedproductattribute_id, attributevalue_id)
                    DO NOTHING
            """,
            (apa_id, attribute.values[0].id))

    # Add Variant
    variant = product.variants[0]
    cursor.execute("""
        INSERT INTO product_productvariant
            (sku, name, product_id, cost_price_amount, weight, metadata, private_metadata,
                currency, price_amount, track_inventory)
        VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
        ON CONFLICT (sku) DO UPDATE
            SET id = product_productvariant.id
        RETURNING id
    """, (variant.sku, variant.name, product.id,
          variant.cost_price_amount, variant.weight,
          variant.metadata, variant.private_metadata,
          variant.currency, variant.price_amount))

    variant.id = cursor.fetchone()[0]
    info(f'Variant ID: {variant.id}')

    try:
        cursor.execute("""
            UPDATE product_product
            SET default_variant_id = %s
            WHERE id = %s
        """, (variant.id, product.id))
    except:
        pass


    # Add To Collections
    collections_to_keep = ()
    if len(product.collections):
        for collection in product.collections:
            collections_to_keep = (*collections_to_keep, collection.id)
            warning(f'Adding to collection: {product.id} in {collection.id}')
            cursor.execute("""
                INSERT INTO product_collectionproduct(collection_id, product_id)
                    VALUES(%s, %s)
                ON CONFLICT (collection_id, product_id)
                DO NOTHING
            """, (collection.id, product.id))

    if len(collections_to_keep):
        # Remove from any other collections
        cursor.execute("""
            DELETE FROM product_collectionproduct
            WHERE product_id = %s AND collection_id NOT IN %s
        """, (product.id, collections_to_keep))
    else:
        # Just remove from all
        cursor.execute("""
            DELETE FROM product_collectionproduct
            WHERE product_id = %s
        """, (product.id,))


    # Add Warehouse entry
    cursor.execute("""
        SELECT id
        FROM warehouse_warehouse
        LIMIT 1""")

    warehouse_id = cursor.fetchone()[0]

    info(f'Creating warehouse entry: {warehouse_id}')
    cursor.execute("""
        INSERT INTO warehouse_stock (product_variant_id, quantity, warehouse_id)
        VALUES(%s, %s, %s)
        ON CONFLICT(product_variant_id, warehouse_id) DO NOTHING
        """, (product.variants[0].id, 0, warehouse_id))

    return True

def handle_images(product: Product, raw_product: dict = None, force_images: bool = False) -> None:
    global oauth_token
    global cursor
    global environment

    raw_images = []
    for i in range(10):
        k = f'Product_Photo{i}'
        if k in raw_product.keys() and raw_product[k] and len(raw_product[k]) > 0:
            raw_images.append(raw_product[k][0])


    s3 = None
    AWS_MEDIA_BUCKET_NAME = os.environ.get("AWS_MEDIA_BUCKET_NAME")
    AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")

    zoho_id = json.loads(product.private_metadata)['ZOHO_ID']

    url = f'https://www.zohoapis.com/crm/v2/Products/{zoho_id}/Attachments'

    headers = {
        'Authorization': f'Zoho-oauthtoken {oauth_token}',
    }

    all_filenames = ()
    for i, image in enumerate(raw_images):
        attachment_id = image['attachment_Id']
        filename = image['file_Name']

        all_filenames = (*all_filenames, f"products/{filename}")

        try:
            # Check if filename exists already
            cursor.execute("""
                SELECT COUNT(*) AS count
                FROM product_productimage
                WHERE product_id = %s and image = %s
            """, (product.id, f"products/{filename}"))

            existing_image = cursor.fetchone()[0]

            # Upload if new or forced
            if not existing_image or force_images is True:
                warning(f'Uploading Image: {filename}')
                session = boto3.Session(
                    aws_access_key_id=AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                )
                s3 = session.resource('s3')

                mtype = mimetypes.MimeTypes().guess_type(filename)[0]

                img_url = f'{url}/{attachment_id}'
                info(img_url)
                req = urllib.request.Request(img_url, headers=headers)
                response = urllib.request.urlopen(req)
                img_bytes = response.read()

                s3.Bucket(AWS_MEDIA_BUCKET_NAME).put_object(
                    Body=img_bytes,
                    Key=f'products/{filename}',
                    ContentType=mtype)

            # Insert or update db
            if not existing_image:
                cursor.execute("""
                    INSERT INTO product_productimage(sort_order, product_id, image, ppoi, alt)
                    VALUES(%s, %s, %s, %s, %s)
                """, (i, product.id, f"products/{filename}", '0.5x0.5', ''))
            else:
                cursor.execute("""
                    UPDATE product_productimage
                    SET sort_order = %s
                    WHERE product_id = %s and image = %s
                """, (i, product.id, f"products/{filename}"))
                warning(f'Existing Image: {filename}')
        except:
            pass

    # Clear out unused photos
    try:
        if len(all_filenames):
            warning("Keep files:")
            warning(all_filenames)
            cursor.execute("""
                DELETE FROM product_productimage
                WHERE product_id = %s AND image NOT IN %s
            """, (product.id, all_filenames))
        else:
            cursor.execute("""
                DELETE FROM product_productimage
                WHERE product_id = %s
            """, (product.id,))
    except:
        error('Error clearing out unused images.')
        pass


def handle_product_type(pt: ProductType = None) -> int:
    global cursor
    warning('PRODUCT TYPE')

    # The ProductType itself
    cursor.execute("""
        INSERT INTO product_producttype (name, has_variants, is_shipping_required, weight,
                is_digital, slug, metadata, private_metadata)
            VALUES(%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (slug) DO UPDATE
                SET id = product_producttype.id, name = %s
            RETURNING id
                            """, (
                                    # INSERT clause
                                    pt.type, False, True, 0, False, pt.slug, '{}', '{}',
                                    # UPDATE clause
                                    pt.type))

    pt.id = cursor.fetchone()[0]

    # Attributes
    for i, attribute in enumerate(pt.attributes):
        cursor.execute("""
        INSERT INTO product_attribute (name, slug, input_type,
                available_in_grid, visible_in_storefront, filterable_in_dashboard,
                filterable_in_storefront, value_required, storefront_search_position,
                is_variant_only, metadata, private_metadata)
            VALUES(%s, %s, %s, TRUE, TRUE,  TRUE, TRUE, TRUE, 0, FALSE, '{}', '{}')
            ON CONFLICT (slug) DO UPDATE
                SET id = product_attribute.id, name = %s
            RETURNING id
            """, (
                    # INSERT clause
                    attribute.type, attribute.slug, 'dropdown',
                    # UPDATE clause
                    attribute.type
                ))
        pt.attributes[i].id = cursor.fetchone()[0]
        comment(f'Attribute {attribute.type}({i}) : {pt.attributes[i].id}')

        cursor.execute("""
                INSERT INTO product_attributeproduct(attribute_id, product_type_id)
                VALUES(%s, %s)
                ON CONFLICT (attribute_id, product_type_id) DO UPDATE
                    SET id = product_attributeproduct.id
                RETURNING ID
            """, (attribute.id, pt.id))
        pt.attributes[i].assignment_id = cursor.fetchone()[0]
        comment(f'  Assignment ID: {pt.attributes[i].assignment_id }')

        # Attribute Values
        for j, value in enumerate(attribute.values):
            cursor.execute("""
            INSERT INTO product_attributevalue(name, slug, value, attribute_id)
            VALUES(%s, %s, %s, %s)
            ON CONFLICT (attribute_id, slug) DO UPDATE
                SET id = product_attributevalue.id, name = %s, value = %s
            RETURNING id
            """, (
                    # INSERT clause
                    value.value, value.slug, value.slug, pt.attributes[i].id,
                    # UPDATE clause
                    value.value, value.slug
                ))
            pt.attributes[i].values[j].id = cursor.fetchone()[0]
        comment(f'  Value {value.value} : {pt.attributes[i].values[j].id}')


    return pt



def handle_product_category(cat: Category = None) -> Category:
    global cursor
    warning('CATEGORIES')
    cursor.execute("""
            INSERT INTO product_category
            (name, slug, level, description, lft, rght, tree_id,
                background_image, background_image_alt, description_json, parent_id,
                metadata, private_metadata)
            VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (slug) DO UPDATE
                SET id = product_category.id, name = %s
            RETURNING id
        """, (
                # INSERT clause
                cat.name, cat.slug, cat.level, cat.description,
                cat.lft, cat.rght, cat.tree_id,
                cat.background_image, cat.background_image_alt,
                cat.description_json, cat.parent_id,
                '{}', '{}',
                # UPDATE clause
                cat.name
            ))
    cat.id = cursor.fetchone()[0]

    comment(f'{cat.name}: {cat.id}')

    for i, child_cat in enumerate(cat.children):
        cat.children[i].parent_id = cat.id
        child_cat.parent_id = cat.id

        cursor.execute("""
                INSERT INTO product_category
                (name, slug, level, description, lft, rght, tree_id,
                    background_image, background_image_alt, description_json, parent_id,
                    metadata, private_metadata)
                VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (slug) DO UPDATE
                    SET id = product_category.id, name = %s
                RETURNING id
            """, (
                    # INSERT clause
                    child_cat.name, child_cat.slug, child_cat.level, child_cat.description,
                    child_cat.lft, child_cat.rght, child_cat.tree_id,
                    child_cat.background_image, child_cat.background_image_alt,
                    child_cat.description_json, child_cat.parent_id,
                    '{}', '{}',
                    # UPDATE clause
                    child_cat.name
                ))

        cat.children[i].id = cursor.fetchone()[0]
        comment(f'  {child_cat.name}: {cat.children[i].id}')

    return cat


def handle_product_collection(collections: list = None) -> None:
    global cursor
    warning('COLLECTIONS')

    for c, collection in enumerate(collections):
        cursor.execute("""
                INSERT INTO product_collection
                    (name, slug, background_image, seo_description, seo_title,
                    is_published, description,
                    publication_date, background_image_alt, description_json,
                    metadata, private_metadata)
                VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(slug) DO UPDATE
                    SET id = product_collection.id, name = %s
                RETURNING id
            """, (
                    # INSERT clause
                    collection.name, collection.slug, '', '', '', 'True', '',
                    'NOW()', '', '{}', '{}', '{}',
                    # UPDATE clause
                    collection.name
                ))

        collections[c].id = cursor.fetchone()[0]
        comment(f'{collection.name}: {collection.id}')
    return collections



def fix_category_hierarchy():
    info('===== FIXING HIERARCHY =====')

    global db
    """
    Note: this only is going to work for 2-level category hierarchies, as the data
    given for the import is set up that way.
    :return:
    """
    warning("Rebuilding category hierarchy")

    # Rebuild the category nested set hierarchy (◔_◔)
    cursor = db.cursor(cursor_factory=DictCursor)

    fields = ['id', 'name', 'slug', 'lft', 'rght', 'tree_id', 'level', 'parent_id']
    cursor.execute("""SELECT * FROM product_category""")

    categories = []
    for result in cursor.fetchall():
        category = Category(result['name'])
        for f in fields:
            setattr(category, f, result[f])
        categories.append(category)

    for cat in categories:
        if cat.parent_id:
            parent = next((p for p in categories if p.id == cat.parent_id), None)
            if parent is None:
                error(
                    f'Cannot find parent category for "{cat.name}" (pid {cat.parent_id})')
                return False
            else:
                parent.children.append(cat)

    parent_categories = list(filter(lambda c: c.parent_id is None, categories))

    tid = 1
    for pc in parent_categories:
        left = 1
        pc.tree_id = tid
        pc.lft = left
        left += 1
        for child in pc.children:
            child.lft = left
            child.rght = left + 1
            child.tree_id = tid
            child.level = 1
            left += 2
        pc.rght = left
        tid += 1

    # Write to db
    for pc in parent_categories:
        for c in [pc] + pc.children:
            comment(f'Updating hierarchy for {c.name} ({c.id}).')
            try:
                cursor.execute("""
                    UPDATE product_category
                        SET lft = %s, rght = %s, tree_id = %s, level = %s
                        WHERE id = %s
                """, (c.lft, c.rght, c.tree_id, c.level, c.id))
            except Exception as e:
                error(f'Cannot set hierarchy: "{c.name}" ({c.id}).')
                error(e)
                return False
    return True


def disable_products(products_to_disable=None):
    global cursor
    if products_to_disable is None:
        return True

    skus = tuple(str(p['SKU']).strip("'") for p in products_to_disable if p['SKU'])

    if len(skus) < 1:
        return 0

    warning(f'Disabling {len(skus)} Products')

    cursor.execute("""
        UPDATE product_product p
        SET is_published = FALSE
        FROM product_productvariant pv
        WHERE pv.product_id = p.id AND pv.sku in %s
    """, (skus,))

    return len(products_to_disable)

def do_import(arguments = None):
    info('===== RUNNING IMPORT =====')

    global oauth_token
    global cursor
    environment = 'production'
    if '--local' in arguments:
        del arguments[0]
        environment = 'local'
        load_dotenv()

    sync_all = False
    force_images = False
    if '--sync-all' in arguments:
        sync_all = True

    if '--force-images' in arguments:
        force_images = True

    db = db_connect(environment)
    if not db:
        error('Cannot connect to database.')
        return False

    cursor = db.cursor()

    if not get_oauth():
        error("Could not retrieve updated access token.")
        return False

    url = 'https://www.zohoapis.com/crm/v2/Products'

    headers = {
        'Authorization': f'Zoho-oauthtoken {oauth_token}'
    }

    # Limit the amount of calls we need to make by only grabbing changes
    # within the last 48 hours
    # (should also be enough to catch a failed sync or two)
    # can override with --sync-all flag
    if not sync_all:
        last_modified = datetime.now() - timedelta(hours=48)
        modified_since = f'{last_modified.strftime("%Y-%m-%d")}T00:00:00+05:00'
        headers['If-Modified-Since'] = modified_since

    parameters = {
        'page': 1,
        'per_page': 200,
    }

    keep_going = True

    while keep_going:

        info(f'Fetching page {parameters["page"]}')
        response = requests.get(url=url, headers=headers, params=parameters)

        if response is not None:
            data = response.json()
            response_info = data['info']

            products = list(filter(lambda x: x['Web_Available'] is True, data['data']))
            remove_products = list(filter(lambda x: x['Web_Available'] is False, data['data']))

            for product in products:
                """
                example `product`:

                {
                    '$approval': {
                        'approve': False,
                        'delegate': False,
                        'reject': False,
                        'resubmit': False
                    },
                    '$approval_state': 'approved',
                    '$approved': True,
                    '$currency_symbol': '$',
                    '$editable': True,
                    '$in_merge': False,
                    '$orchestration': False,
                    '$process_flow': False,
                    '$review': None,
                    '$review_process': {
                        'approve': False,
                        'reject': False,
                        'resubmit': False
                    },
                    '$state': 'save',
                    '$taxable': True,
                    'Attribute_Name_1': 'Style',
                    'Attribute_Name_2': 'Joint Size',
                    'Attribute_Name_3': 'Brand',
                    'Attribute_Name_4': None,
                    'Attribute_Name_5': None,
                    'Attribute_Name_6': None,
                    'Attribute_Value_1': 'Slide',
                    'Attribute_Value_2': '14mm',
                    'Attribute_Value_3': 'NA',
                    'Attribute_Value_4': None,
                    'Attribute_Value_5': None,
                    'Attribute_Value_6': None,
                    'Category': 'Slides',
                    'Collection': None,
                    'Cost': 3.5,
                    'Created_Time': '2021-04-30T13:49:13-04:00',
                    'Department': 'Smoke Shop',
                    'Description': None,
                    'Margin': 76.651,
                    'Needs_Reviewed': True,
                    'Owner': {
                        'email': 'planetcaravan513@gmail.com',
                        'id': '3980137000000211013',
                        'name': 'Planet Caravan'
                    },
                    'Product_Name': 'Got Vape - FGA366 Yellow/Black 14mm Slide | 400000236445',
                    'Product_Photos': None,
                    'Record_Image': None,
                    'SKU': "400000236445'",
                    'Supplier': 'Got Vape',
                    'Tag': [],
                    'Tax': [],
                    'Taxable': True,
                    'UPC': None,
                    'Unit_Price': 14.99,
                    'Web_Available': True,
                    'id': '3980137000009112120'
                }
                """
                handle_raw_product(product, {
                    'force_images': force_images
                })

            disable_products(remove_products)

            parameters['page'] += 1
            keep_going = response_info['more_records']
        else:
            keep_going = False

    return True


def bust_cache():
    info('===== CLEARING CACHE =====')
    qk = cache.keys("query-*")
    cache.delete_many(qk)
    return True


if __name__ == '__main__':
    result = (do_import(sys.argv[1:]) and
              fix_category_hierarchy() and
              bust_cache())
    if result:
        warning('Done.')
    else:
        error("Completed with errors. There is likely output above.")
        sys.exit(1)
