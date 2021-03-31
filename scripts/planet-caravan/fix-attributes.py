import sys
from dotenv import load_dotenv
from Lib.CLI import *
from Lib.helpers import handleize
from Lib.Saleor.Saleor import Saleor
import os
import psycopg2
import psycopg2.extras

# Global variable
cursor = None

def db_connect(environment = 'local'):
    info("Connecting to DB")
    db = None

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


def get_attributes_by_type(type_id):
    global cursor

    attributes = {}
    try:
        cursor.execute("""
        SELECT *
            FROM product_attributeproduct
            WHERE product_type_id = %s
        """, (type_id,))

        att = cursor.fetchall()

        for a in att:
            attributes[a['attribute_id']] = dict(a)


        return attributes
    except Exception as e:
        error(f'Cannot get attributes for product type id {type_id}.')
        error(e)


def get_attribute_values(attribute):
    global cursor

    attribute['values'] = {}

    try:
        cursor.execute("""
            SELECT *
            FROM product_attributevalue
            WHERE attribute_id = %s
            """, (attribute['attribute_id'],))

        values = cursor.fetchall()

        for v in values:
            attribute['values'][v['id']] = dict(v)

        return attribute
    except Exception as e:
        error(f'Cannot get values for attribute id {attribute["attribute_id"]}.')
        error(e)


def get_product_assigned_attributes(product_id):
    global cursor
    assigned = {}

    try:
        cursor.execute("""
            SELECT apv.id,
                apv.assignedproductattribute_id, apv.attributevalue_id, av.id AS value_id, av.name,
                ap.attribute_id
            FROM product_assignedproductattribute_values apv
            LEFT JOIN product_attributevalue av ON av.id = apv.attributevalue_id
            LEFT JOIN product_assignedproductattribute apa ON apa.id = apv.assignedproductattribute_id
            LEFT JOIN product_attributeproduct ap ON ap.id = apa.assignment_id
            WHERE apa.product_id = %s
            """, (product_id,))

        values = cursor.fetchall()

        for v in values:
            assigned[v['assignedproductattribute_id']] = dict(v)

        return assigned
    except Exception as e:
        error(f'Cannot get attributes for product type id {type_id}.')
        error(e)


def change_attribute_value_id(assignment_id, value_id):
    global cursor

    try:
        cursor.execute("""
            UPDATE product_assignedproductattribute_values
             SET attributevalue_id = %s
             WHERE id = %s
            """, (value_id, assignment_id))
        return True

    except Exception as e:
        error(f'Cannot update assignment ID {assignment_id} to {value_id}.')
        error(e)

def create_new_attribute_value(attribute_id, value):
    global cursor

    slug = handleize(value)
    try:
        cursor.execute("""
                INSERT INTO product_attributevalue
                (name, attribute_id, slug, value) VALUES (%s, %s, %s, %s)
                RETURNING id
                """, (value, attribute_id, slug, ""))
        value_id = cursor.fetchone()[0]

        return {
            'id': value_id,
            'name': value,
            'attribute_id': attribute_id,
            'slug': slug,
            'sort_order': None,
            'value': ''
        }

    except Exception as e:
        error(f'Cannot create new value {attribute_id}: {value}.')
        error(e)

def fix_things(arguments):
    global cursor
    environment = 'production'
    if len(arguments) >= 2 and arguments[1] == '--local':
        del arguments[1]
        environment = 'local'
        load_dotenv()

    db = db_connect(environment)
    if not db:
        return

    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)

    product_type_attributes = {}
    attributes = {}

    """
    This is going to be horribly inefficient but should only need to run once
    so I don't really care.
    """
    try:
        cursor.execute("""SELECT * from product_product""")
        products = cursor.fetchall()

        for product in products:
            info(product['name'])

            # Get valid attributes
            if product['product_type_id'] not in product_type_attributes.keys():
                att = get_attributes_by_type(product['product_type_id'])
                product_type_attributes[product['product_type_id']] = att
            else:
                att = product_type_attributes[product['product_type_id']]

            for attribute_id, attribute in att.items():
                if attribute_id not in attributes.keys():
                    att_detail = get_attribute_values(attribute)
                    attributes[attribute_id] = att_detail

            # Get this product's attributes
            product_attributes = get_product_assigned_attributes(product['id'])
            # comment('ATTRIBUTES:')
            # warning(product_attributes)

            for assignment_id, attribute in product_attributes.items():
                if attribute['attribute_id'] not in attributes.keys():
                    error(f'Attribute id {attribute["attribute_id"]} not in attributes object.')
                    return

                associated_attribute = attributes[attribute['attribute_id']]

                comment(f"{attribute['attributevalue_id']}: {attribute['name']}")
                if attribute['attributevalue_id'] in associated_attribute['values'].keys():
                    # Seems fine
                    continue

                #####
                """
                Here's the real fix
                """
                #####

                """
                Check that there's not a matching value with a different ID
                Especially if we are correcting multiple products in the same
                script run with the same issue
                """

                desired_value = attribute['name']
                match = list(filter(lambda x: x['name'] == desired_value, associated_attribute['values'].values()))

                # DEV
                if len(match):
                    warning('Matched on other attribute, changing value ID in assignment.')
                    warning(f"{attribute['id']} : {match[0]['id']}")
                    change_attribute_value_id(attribute['id'], match[0]['id'])
                else:
                    new_value = create_new_attribute_value(attribute['attribute_id'], desired_value)
                    warning(f"Created new attribute value {attribute['id']} : {desired_value}")

                    if new_value and 'id' in new_value.keys():
                        attributes[attribute['attribute_id']]['values'][new_value['id']] = new_value
                        change_attribute_value_id(attribute['id'], new_value['id'])



    except Exception as e:
        error(f'Cannot get products.')
        error(e)


if __name__ == '__main__':
    fix_things(sys.argv)
