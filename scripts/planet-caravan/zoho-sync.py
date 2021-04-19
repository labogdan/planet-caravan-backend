import json
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


def handle_raw_product(raw_product: dict = None):
    global cursor

    print('======================================')
    warning(f'handle_raw_product(): {raw_product["Product_Name"]}')

    # Product
    product = Product()
    product.name = raw_product['Product_Name']
    product.slug = handleize(raw_product['Product_Name'])
    product.description = raw_product['Description_of_Product']
    product.description_json = description_block(raw_product['Description_of_Product'])
    product.metadata = '{}'
    product.private_metadata = json.dumps({
        'ZOHO_ID': raw_product['id']
    })

    # Variant
    variant = Variant()
    variant.name = raw_product['Product_Name']
    variant.sku = raw_product['SKU']
    variant.cost_price_amount = raw_product['Cost']
    variant.weight = 0
    variant.price_amount = raw_product['Unit_Price']

    product.variants.append(variant)

    # Product type
    pt = ProductType()
    pt.type = raw_product['Category']
    pt.slug = handleize(raw_product['Category'])

    # Category
    parent_category = Category(raw_product['Category'])

    child_category = Category(raw_product['Collection'])
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

    # Collection
    collection = ProductCollection()
    collection.name = raw_product['Collection']
    collection.slug = handleize(raw_product['Collection'])

    product.collections.append(collection)

    create_or_update_data(product)


def create_or_update_data(product: Product = None):
    global cursor
    info(f'create_or_update_data(): {product.name} | {product.variants[0].sku}')
    product.type = handle_product_type(product.type)
    comment(f'Product type ID: {product.type.id}')

    product.category = handle_product_category(product.category)
    comment(f'Product category ID: {product.category.children[0].id}')

    product.collection = handle_product_collection(product.collections[0])

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
    else:
        cursor.execute("""
               INSERT INTO product_product
               (name, description, description_json, product_type_id, category_id,
               is_published, charge_taxes, currency, slug, visible_in_listings, metadata,
               private_metadata, publication_date, updated_at, available_for_purchase)
               VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW())
               ON CONFLICT (slug) DO UPDATE
                SET id = product_product.id, name = %s,
                    description = %s, description_json = %s, product_type_id = %s,
                    category_id = %s, private_metadata = %s, updated_at = NOW()
               RETURNING id
               """,
           (
                # INSERT clause
                product.name, product.description, product.description_json,
                product.type.id, product.category.id, product.is_published, product.charge_taxes,
                product.currency, product.slug, product.visible_in_listings,
                product.metadata, product.private_metadata,

                # UPDATE clause
                product.name, product.description, product.description_json,
                product.type.id, product.category.id, product.private_metadata
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

        cursor.execute("""
                INSERT INTO product_assignedproductattribute_values
                    (assignedproductattribute_id, attributevalue_id)
                VALUES(%s, %s)
                ON CONFLICT (assignedproductattribute_id, attributevalue_id) DO NOTHING
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

    # Add To Collection
    if product.collection:
        warning(f'Adding to collection: {product.id} in {product.collection.id}')
        cursor.execute("""
            INSERT INTO product_collectionproduct(collection_id, product_id)
                VALUES(%s, %s)
            ON CONFLICT (collection_id, product_id)
            DO NOTHING
        """, (product.collection.id, product.id))

    return True


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
        info(f'Attribute {i}: {attribute}')
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
        comment(f'Attribute {attribute.type} : {pt.attributes[i].id}')

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


def handle_product_collection(collection: ProductCollection = None) -> ProductCollection:
    global cursor
    warning('COLLECTION')

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

    collection.id = cursor.fetchone()[0]
    comment(f'{collection.name}: {collection.id}')

    return collection


def fix_category_hierarchy():
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

def do_import(arguments):
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
        'per_page': 5,
    }

    keep_going = True

    while keep_going:

        info(f'Fetching page {parameters["page"]}')
        response = requests.get(url=url, headers=headers, params=parameters)

        if response is not None:
            data = response.json()
            response_info = data['info']

            products = list(filter(lambda x: x['Web_Available'] is True, data['data']))

            # DEV FILTER
            products = list(
                filter(lambda x: 'Website Test' in x['Product_Name'], products))

            for product in products:
                handle_raw_product(product)

            parameters['page'] += 1
            keep_going = response_info['more_records']
        else:
            keep_going = False


if __name__ == '__main__':
    do_import(sys.argv[1:])
    print('')
    fix_category_hierarchy()
    print('')
    warning('Done.')
