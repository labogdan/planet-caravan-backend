from Lib.CLI import *
import os
import pandas as pd
import psycopg2
import psycopg2.extras
import boto3
from Lib.Saleor.Category import Category
from Lib.Saleor.Product import Product
from Lib.Saleor.ProductCollection import ProductCollection
from Lib.Saleor.ProductAttribute import ProductAttribute
from Lib.Saleor.ProductAttributeValue import ProductAttributeValue
from Lib.Saleor.ProductType import ProductType
from Lib.Saleor.Variant import Variant
from Lib.helpers import handleize
from Lib.helpers import has_value
import urllib.request
import random
import string


class Saleor:
    # CSV header constants
    TYPE_KEY = "Category"
    OPTION_HEADERS = [
        ('Option1 Name (Do Not Edit)', 'Option1 Value (Do Not Edit)'),
        ('Option2 Name (Do Not Edit)', 'Option2 Value (Do Not Edit)'),
        ('Option3 Name (Do Not Edit)', 'Option3 Value (Do Not Edit)')
    ]
    ATTRIBUTE_HEADERS = [
        ('Attribute Name 1', 'Attribute Value 1'),
        ('Attribute Name 2', 'Attribute Value 2'),
        ('Attribute Name 3', 'Attribute Value 3')
    ]
    IMPORT_SKU = 'SKU (Do Not Edit)'
    INVENTORY_SKU = 'Store Code (SKU)'
    IMAGES = [f'Photo {x}' for x in range(1, 3)]

    def __init__(self, environment):
        self.db = None
        self.product_types = []
        self.collections = {}
        self.categories = {}
        self.attribute_assignments = {}
        self.environment = environment
        self.warehouse_id = None

    def update_stock(self, file=''):
        """
        Regularly-scheduled inventory sync by SKU
        :param file:
        :return:
        """
        info(f'Updating stock from {file}')
        df = pd.read_csv(file)

        self.db_connect()
        self.get_warehouse()

        cursor = self.db.cursor()

        for (i, row) in df.iterrows():
            sku = str(row.loc[Saleor.INVENTORY_SKU])
            inventory = int(row.loc['Quantity'])

            info(f'Updating {sku} to {inventory}')

            cursor.execute("""
            UPDATE warehouse_stock
                SET quantity = %s
                FROM product_productvariant
                WHERE product_productvariant.id = warehouse_stock.product_variant_id
                    AND LOWER(product_productvariant.sku) = %s
                    AND warehouse_stock.warehouse_id = %s
            """, (inventory, str(sku).lower(), self.warehouse_id))

    def import_all(self, file='', image_base=''):
        """
        Imports an entire store's data
        Should only be run on a new saleor store; not really designed to handle existing data in store (especially categories)
        :param file:
        :param photo_input:
        :param photo_output:
        :return:
        """
        warning(f'Importing products from {file}')
        df = pd.read_csv(file)

        if not self.db_connect():
            return False

        # Run the process
        result = (self.get_warehouse() and
                  self.create_types_attributes(df.copy()) and
                  self.create_collections(df.copy()) and
                  self.create_categories(df.copy()) and
                  self.fix_category_hierarchy() and
                  self.create_products(df.copy()) and
                  self.upload_images(df.copy(), image_base))
        print()

        if result:
            info("Done")
        else:
            error("Completed with errors. There is likely output above.")

        return result

    def db_connect(self):
        info("Connecting to DB")

        try:
            if self.environment == 'local':
                # Local dev
                db_name = os.getenv('DB_NAME')
                db_user = os.getenv('DB_USER')
                db_host = os.getenv('DB_HOST')
                db_pass = os.getenv('DB_PASS')

                self.db = psycopg2.connect(
                    f"dbname='{db_name}' user='{db_user}' host='{db_host}' password='{db_pass}'")
            else:
                # Heroku Production
                db_host = os.environ['DATABASE_URL']
                self.db = psycopg2.connect(db_host, sslmode='require')

            self.db.autocommit = True
            return True
        except Exception as e:
            error("Unable to connect to database.")
            error(e)
            return False

    def get_warehouse(self):
        cursor = self.db.cursor()

        try:
            cursor.execute("""
                SELECT id
                FROM warehouse_warehouse
                LIMIT 1""")

            result = cursor.fetchone()
            if result is None:
                error('No warehouse set up.')
                warning('Create one via the Saleor dashbboard.')
            else:
                self.warehouse_id = result[0]
                comment(f'Warehouse found: {self.warehouse_id}')
                return True

        except Exception as e:
            error(f'Cannot get warehouse ID.')
            error(e)
        return False

    def create_types_attributes(self, df):
        info("Setting up Product types and attributes")

        type_group = df.groupby([Saleor.TYPE_KEY])

        product_types = []
        for type_name, frame in type_group:
            product_type = ProductType(type_name.strip())
            # Variant Options
            for (option_name, option_value) in Saleor.OPTION_HEADERS:

                option_names = list(set([
                    d.strip() for d in frame[option_name]
                    if has_value(d)
                ]))

                option_values = list(set([
                    d.strip() for d in frame[option_value]
                    if has_value(d)
                ]))

                if len(option_names) > 1:
                    error(
                        f'Product type options do not match: {type_name} ({option_names}).')
                    return False

                if len(option_names) == 1:
                    # Check that it wasn't an empty line
                    opt_values = [ProductAttributeValue(v.strip()) for v in
                                  option_values]
                    product_attribute = ProductAttribute(option_names[0].strip(),
                                                         opt_values)
                    product_type.add_variant_attribute(product_attribute)

            # Product Attributes
            for (attribute_name, attribute_value) in Saleor.ATTRIBUTE_HEADERS:

                attribute_names = list(set([
                    d.strip() for d in frame[attribute_name]
                    if has_value(d)
                ]))

                attribute_values = list(set([
                    d.strip() for d in frame[attribute_value]
                    if has_value(d)
                ]))

                if len(attribute_names) > 1:
                    error(
                        f'Product attribute options do not match: {type_name} ({attribute_names}).')
                    return False

                if len(attribute_names) == 1:
                    # Check that it wasn't an empty line
                    att_values = [ProductAttributeValue(v.strip()) for v in
                                  attribute_values]
                    product_attribute = ProductAttribute(attribute_names[0].strip(),
                                                         att_values)
                    product_type.add_attribute(product_attribute)

            product_types.append(product_type)

        cursor = self.db.cursor()

        # Create in the database
        for product_type in product_types:
            # Check if it exists, if not, create
            try:
                cursor.execute("""
                    SELECT id
                    FROM product_producttype
                    WHERE LOWER(slug) = %s
                    LIMIT 1""", (product_type.slug,))

                result = cursor.fetchone()
                if result is None:
                    # Create product type
                    cursor.execute("""
                        INSERT INTO product_producttype
                        (name, has_variants, is_shipping_required, weight, is_digital,
                        slug, metadata, private_metadata)
                        VALUES(%s, %s, TRUE, 250, FALSE, %s, '{}', '{}')
                        RETURNING id
                    """, (product_type.type,
                          'TRUE' if len(product_type.variant_attributes) else 'FALSE',
                          product_type.slug))

                    product_type.id = cursor.fetchone()[0]
                    comment(f'Product Type {product_type.type} - Created')
                else:
                    product_type.id = result[0]
                    comment(f'Product Type {product_type.type} - Found')

            except Exception as e:
                error(f'Cannot upsert ProductType "{product_type.type}".')
                error(e)
                return False

            """
            Create the variant attributes for this product Type
            """
            for v_attribute in product_type.variant_attributes:
                try:
                    v_attribute.slug = handleize(
                        f'{v_attribute.type}-{product_type.type}')
                    cursor.execute("""
                        SELECT id
                        FROM product_attribute
                        WHERE LOWER(slug) = %s
                        LIMIT 1""", (v_attribute.slug,))

                    result = cursor.fetchone()
                    if result is None:
                        # Create attribute
                        cursor.execute("""
                            INSERT INTO product_attribute
                            (name, slug, input_type, available_in_grid, visible_in_storefront,
                                filterable_in_dashboard, filterable_in_storefront, value_required,
                                storefront_search_position, is_variant_only,
                                metadata, private_metadata)
                            VALUES(%s, %s, %s, TRUE, TRUE, TRUE, TRUE, TRUE, 0, FALSE, '{}', '{}')
                            RETURNING id
                        """, (v_attribute.type, v_attribute.slug, 'dropdown'))

                        v_attribute.id = cursor.fetchone()[0]
                        comment(f'Variant Attribute {v_attribute.type} - Created')
                    else:
                        v_attribute.id = result[0]
                        comment(f'Variant Attribute {v_attribute.type} - Found')
                except Exception as e:
                    error(f'Cannot upsert Variant Attribute "{v_attribute.type}".')
                    error(e)
                    return False

                # Add attribute values
                for value in v_attribute.values:
                    try:
                        cursor.execute("""
                            SELECT id
                            FROM product_attributevalue
                            WHERE LOWER(slug) = %s
                            LIMIT 1""", (value.slug,))

                        result = cursor.fetchone()
                        if result is None:
                            # Create attribute value
                            cursor.execute("""
                            INSERT INTO product_attributevalue(name, slug, value, attribute_id)
                            VALUES(%s, %s, %s, %s)
                            ON CONFLICT (attribute_id, slug) DO NOTHING
                            RETURNING id
                        """, (value.value, value.slug, value.slug, v_attribute.id))

                            value.id = cursor.fetchone()[0]
                            comment(f'Variant Attribute Value {value.value} - Created')
                        else:
                            value.id = result[0]
                            comment(f'Variant Attribute Value {value.value} - Found')
                    except Exception as e:
                        error(
                            f'Cannot add Value "{value.value}" ({value.slug}) to Variant Attribute "{v_attribute.type}".')
                        error(e)
                        return False

                try:
                    # Add variant attribute to this product type
                    cursor.execute("""
                                SELECT id
                                FROM product_attributevariant
                                WHERE attribute_id = %s AND product_type_id = %s
                                LIMIT 1""", (v_attribute.id, product_type.id))
                    result = cursor.fetchone()
                    if result is None:
                        cursor.execute("""
                            INSERT INTO product_attributevariant(attribute_id, product_type_id)
                            VALUES(%s, %s)
                            ON CONFLICT (attribute_id, product_type_id) DO NOTHING
                            RETURNING ID
                        """, (v_attribute.id, product_type.id))

                        assignment_id = cursor.fetchone()[0]
                    else:
                        assignment_id = result[0]

                except Exception as e:
                    error(
                        f'Cannot add Variant Attribute "{v_attribute.type}" to Product Type "{product_type.type}".')
                    error(e)
                    return False

                if product_type.id not in self.attribute_assignments.keys():
                    self.attribute_assignments[product_type.id] = {}

                self.attribute_assignments[product_type.id][
                    v_attribute.id] = assignment_id

            """
            Create the product attributes for this product Type
            """
            for attribute in product_type.attributes:
                try:
                    # attribute.slug = handleize(
                    #     f'{attribute.type}-{product_type.type}')
                    cursor.execute("""
                                    SELECT id
                                    FROM product_attribute
                                    WHERE LOWER(slug) = %s
                                    LIMIT 1""", (attribute.slug,))

                    result = cursor.fetchone()
                    if result is None:
                        # Create attribute
                        cursor.execute("""
                                        INSERT INTO product_attribute
                                        (name, slug, input_type, available_in_grid, visible_in_storefront,
                                            filterable_in_dashboard, filterable_in_storefront, value_required,
                                            storefront_search_position, is_variant_only,
                                            metadata, private_metadata)
                                        VALUES(%s, %s, %s, TRUE, TRUE, TRUE, TRUE, TRUE, 0, FALSE, '{}', '{}')
                                        RETURNING id
                                    """, (
                            attribute.type, attribute.slug, 'dropdown'))

                        attribute.id = cursor.fetchone()[0]
                        comment(f'Attribute {attribute.type} - Created')
                    else:
                        attribute.id = result[0]
                        comment(f'Attribute {attribute.type} - Found')
                except Exception as e:
                    error(f'Cannot upsert Attribute "{attribute.type}".')
                    error(e)
                    return False

                # Add attribute values
                for value in attribute.values:
                    try:
                        cursor.execute("""
                                        SELECT id
                                        FROM product_attributevalue
                                        WHERE LOWER(slug) = %s
                                        LIMIT 1""", (value.slug,))

                        result = cursor.fetchone()
                        if result is None:
                            # Create attribute value
                            cursor.execute("""
                                        INSERT INTO product_attributevalue(name, slug, value, attribute_id)
                                        VALUES(%s, %s, %s, %s)
                                        ON CONFLICT (attribute_id, slug) DO NOTHING
                                        RETURNING id
                                    """, (
                                value.value, value.slug, value.slug, attribute.id))

                            value.id = cursor.fetchone()[0]
                            comment(f'Attribute Value {value.value} - Created')
                        else:
                            value.id = result[0]
                            comment(f'Attribute Value {value.value} - Found')
                    except Exception as e:
                        error(
                            f'Cannot add Value "{value.value}" ({value.slug}) to Attribute "{attribute.type}".')
                        error(e)
                        return False

                try:
                    # Add product attribute to this product type
                    cursor.execute("""
                                SELECT id
                                FROM product_attributeproduct
                                WHERE attribute_id = %s AND product_type_id = %s
                                LIMIT 1""", (attribute.id, product_type.id))
                    result = cursor.fetchone()
                    if result is None:
                        cursor.execute("""
                            INSERT INTO product_attributeproduct(attribute_id, product_type_id)
                            VALUES(%s, %s)
                            ON CONFLICT (attribute_id, product_type_id) DO NOTHING
                            RETURNING ID
                        """, (attribute.id, product_type.id))

                        assignment_id = cursor.fetchone()[0]
                    else:
                        assignment_id = result[0]

                except Exception as e:
                    error(
                        f'Cannot add Variant Attribute "{attribute.type}" to Product Type "{product_type.type}".')
                    error(e)
                    return False

                if product_type.id not in self.attribute_assignments.keys():
                    self.attribute_assignments[product_type.id] = {}
                self.attribute_assignments[product_type.id][
                    attribute.id] = assignment_id

        self.product_types = product_types

        return True

    def create_collections(self, df):
        info("Setting up Product collections")

        collections_group = df.groupby(['Collections'])

        for collection_group, frame in collections_group:
            collection_names = collection_group.split(',')
            for collection_name in collection_names:
                cname = collection_name.strip()
                product_collection = ProductCollection(cname)
                self.collections[cname] = product_collection

        cursor = self.db.cursor()

        for cname, collection in self.collections.items():
            try:
                cursor.execute("""
                    SELECT id
                    FROM product_collection
                    WHERE LOWER(slug) = %s
                    LIMIT 1""", (str(collection.slug).lower(),))

                result = cursor.fetchone()
                if result is None:
                    # Create collection
                    cursor.execute("""
                        INSERT INTO product_collection
                        (name, slug, background_image, seo_description, seo_title,
                            is_published, description,
                            publication_date, background_image_alt, description_json,
                            metadata, private_metadata)
                        VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (collection.name, collection.slug, '', '', '', 'True', '',
                          'NOW()', '', '{}', '{}', '{}'))

                    collection.id = cursor.fetchone()[0]
                    comment(f'Collection {collection.name} - Created')
                else:
                    collection.id = result[0]
                    comment(f'Collection {collection.name} - Found')

                self.collections[cname] = collection

            except Exception as e:
                error(f'Cannot upsert Collection "{collection.name}".')
                error(e)
                return False
        return True

    def create_categories(self, df):
        info("Creating categories")
        categories_group = df.groupby(['Department', 'Category'])

        cursor = self.db.cursor()

        categories = {}
        for (parent_cat_name, child_cat_name), frame in categories_group:
            pcs = handleize(parent_cat_name)

            # Parent category
            if pcs in categories.keys():
                parent_cat = categories[pcs]
            else:
                parent_cat = Category(parent_cat_name.strip())
                try:
                    cursor.execute("""
                        SELECT id
                        FROM product_category
                        WHERE LOWER(slug) = %s AND parent_id IS NULL
                        LIMIT 1""", (parent_cat.slug,))

                    result = cursor.fetchone()
                    if result is None:
                        # Create parent category
                        cursor.execute("""
                            INSERT INTO product_category
                            (name, slug, level, description, lft, rght, tree_id,
                                background_image, background_image_alt, description_json, parent_id,
                                metadata, private_metadata)
                            VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING id
                        """, (parent_cat.name, parent_cat.slug, parent_cat.level,
                              parent_cat.description,
                              parent_cat.lft, parent_cat.rght, parent_cat.tree_id,
                              parent_cat.background_image,
                              parent_cat.background_image_alt,
                              parent_cat.description_json, parent_cat.parent_id,
                              '{}', '{}'))

                        parent_cat.id = cursor.fetchone()[0]
                        comment(f'Parent category {parent_cat.name} - Created')
                    else:
                        parent_cat.id = result[0]
                        comment(f'Parent category {parent_cat.name} - Found')

                    categories[parent_cat.slug] = parent_cat
                except Exception as e:
                    error(f'Cannot upsert parent Category "{parent_cat.name}".')
                    error(e)
                    return False

            # Child Category
            child_cat = Category(child_cat_name.strip())
            child_cat.parent_id = parent_cat.id
            child_cat.level = 1

            if child_cat.slug not in categories.keys():
                try:
                    cursor.execute("""
                        SELECT id
                        FROM product_category
                        WHERE LOWER(slug) = %s
                        LIMIT 1""", (child_cat.slug,))

                    result = cursor.fetchone()
                    if result is None:
                        # Create child category
                        cursor.execute("""
                            INSERT INTO product_category
                            (name, slug, level, description, lft, rght, tree_id,
                                background_image, background_image_alt, description_json, parent_id,
                                metadata, private_metadata)
                            VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING id
                        """, (child_cat.name, child_cat.slug, child_cat.level,
                              child_cat.description,
                              child_cat.lft, child_cat.rght, child_cat.tree_id,
                              child_cat.background_image,
                              child_cat.background_image_alt,
                              child_cat.description_json, child_cat.parent_id,
                              '{}', '{}'))

                        child_cat.id = cursor.fetchone()[0]
                        comment(f'Child category {child_cat.name} - Created')
                    else:
                        child_cat.id = result[0]
                        comment(f'Child category {child_cat.name} - Found')

                    categories[child_cat.slug] = child_cat
                except Exception as e:
                    error(f'Cannot upsert child Category "{child_cat.name}".')
                    error(e)
                    return False

        self.categories = categories
        return True

    def fix_category_hierarchy(self):
        """
        Note: this only is going to work for 2-level category hierarchies, as the data
        given for the import is set up that way.
        :return:
        """
        info("Rebuilding category hierarchy")

        # Rebuild the category nested set hierarchy (◔_◔)
        cursor = self.db.cursor(cursor_factory=psycopg2.extras.DictCursor)

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

    def create_products(self, df):
        info("Setting up Products")
        products = df.groupby(["Name"])

        cursor = self.db.cursor()

        row_i = -1
        for product_name, frame in products:
            row_i += 1

            product = Product(product_name.strip())

            row = frame.to_dict('records')[0]

            try:
                cursor.execute("""
                    SELECT id
                    FROM product_product
                    WHERE LOWER(slug) = %s
                    LIMIT 1""", (product.slug,))

                result = cursor.fetchone()
                if result is None:
                    # Create product
                    ptype = next((p for p in self.product_types if
                                  p.type == row[Saleor.TYPE_KEY].strip()), None)
                    category = next((c for c in self.categories.values() if
                                     c.name == row['Category'].strip()), None)
                    comment(f'Category {category}')

                    product.product_type_id = ptype.id if ptype is not None else None
                    product.category_id = category.id if category is not None else None
                    desc = str(row['Description']).strip()
                    product.description = desc
                    product.description_json = self.make_description_block(desc)

                    cursor.execute("""
                        INSERT INTO product_product
                        (name, description, description_json, product_type_id, category_id, is_published, charge_taxes,
                            currency, slug, visible_in_listings, metadata, private_metadata,
                            publication_date, updated_at, available_for_purchase)
                        VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW())
                        RETURNING id
                    """, (product.name, product.description, product.description_json,
                          product.product_type_id,
                          product.category_id,
                          product.is_published, product.charge_taxes,
                          product.currency, product.slug, product.visible_in_listings,
                          product.metadata, product.private_metadata))

                    product.id = cursor.fetchone()[0]
                    comment(f'Product {product.name} - Created')
                else:
                    product.id = result[0]
                    comment(f'Product {product.name} - Found')

            except Exception as e:
                error(f'Cannot upsert Product "{product.name}".')
                error(e)
                return False

            # Add product attributes
            for (att_name_key, att_value_key) in Saleor.ATTRIBUTE_HEADERS:
                att_name = row[att_name_key]
                att_value = row[att_value_key]

                if not has_value(att_name) or not has_value(att_value):
                    continue

                ptype = next((p for p in self.product_types if
                              p.type == row[Saleor.TYPE_KEY].strip()), None)

                if ptype is not None:
                    attribute = next((a for a in ptype.attributes if
                                      a.type == att_name), None)

                    if attribute is not None:
                        attribute_value = next((v for v in attribute.values if
                                                v.value == att_value), None)

                        if attribute_value is not None:
                            assignment_id = self.attribute_assignments[ptype.id][
                                attribute.id]
                            try:
                                cursor.execute("""
                                                SELECT id
                                                FROM product_assignedproductattribute
                                                WHERE product_id = %s AND assignment_id = %s
                                                LIMIT 1""",
                                               (product.id, assignment_id))

                                result = cursor.fetchone()
                                if result is None:
                                    # Assign variant attribute
                                    cursor.execute("""
                                                    INSERT INTO product_assignedproductattribute(product_id, assignment_id)
                                                    VALUES(%s, %s)
                                                    ON CONFLICT (product_id, assignment_id) DO NOTHING
                                                    RETURNING id
                                                """,
                                                   (product.id, assignment_id))

                                    assignedproductattribute_id = cursor.fetchone()[0]
                                else:
                                    assignedproductattribute_id = result[0]
                            except Exception as e:
                                error(
                                    f'Cannot upsert Assigned Product Attribute "{product.id}:{assignment_id}".')
                                error(e)
                                return False

                            try:
                                cursor.execute("""
                                                INSERT INTO product_assignedproductattribute_values
                                                    (assignedproductattribute_id, attributevalue_id)
                                                VALUES(%s, %s)
                                                ON CONFLICT (assignedproductattribute_id, attributevalue_id) DO NOTHING
                                                RETURNING id
                                            """,
                                               (assignedproductattribute_id,
                                                attribute_value.id))

                            except Exception as e:
                                error(
                                    f'Cannot upsert Assigned Product Attribute Values' +
                                    f'"{assignedproductattribute_id}:{attribute_value.id}".')
                                error(e)
                                return False

            # Add product to collections
            collections = row['Collections'].split(',')
            for cname in collections:
                cname = cname.strip()
                if cname not in self.collections.keys():
                    error(f'Collection not in index: {cname}')
                    return False

                collection = self.collections[cname]
                try:
                    cursor.execute("""
                        INSERT INTO product_collectionproduct(collection_id, product_id, sort_order)
                            VALUES(%s, %s, %s)
                        ON CONFLICT (collection_id, product_id)
                        DO NOTHING
                        """, (collection.id, product.id, row_i))

                except Exception as e:
                    error(
                        f'Cannot add product to collection ({product.name} : {cname}).')
                    error(e)
                    return False

            # Create each variant
            for (idx, v) in frame.iterrows():
                name = v.loc['Name']

                for (opt_name_header, opt_value_header) in Saleor.OPTION_HEADERS:
                    opt_header = v.loc[opt_name_header]
                    opt_value = v.loc[opt_value_header]
                    if not has_value(opt_header) or not has_value(opt_value):
                        continue
                    opt_value = opt_value.strip()
                    name += f' / {opt_value}'

                variant = Variant(name, product.id)
                variant.sku = str(v[Saleor.IMPORT_SKU]).strip("'").strip()
                variant.price_amount = v['Price']
                variant.cost_price_amount = v['Cost']

                try:
                    cursor.execute("""
                        SELECT id
                        FROM product_productvariant
                        WHERE LOWER(sku) = %s
                        LIMIT 1""", (str(variant.sku).lower(),))

                    result = cursor.fetchone()
                    if result is None:
                        # Create variant

                        cursor.execute("""
                            INSERT INTO product_productvariant
                                (sku, name, product_id, cost_price_amount, weight, metadata, private_metadata,
                                    currency, price_amount, track_inventory)
                            VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                            RETURNING id
                        """, (variant.sku, variant.name, variant.product_id,
                              variant.cost_price_amount, variant.weight,
                              variant.metadata, variant.private_metadata,
                              variant.currency, variant.price_amount))

                        variant.id = cursor.fetchone()[0]
                        comment(f' - Variant {variant.name} - Created')
                    else:
                        variant.id = result[0]
                        comment(f' - Variant {variant.name} - Found')

                except Exception as e:
                    error(f'Cannot upsert Variant "{variant.name}".')
                    error(e)
                    return False

                # Add Inventory
                try:
                    cursor.execute("""
                        INSERT INTO warehouse_stock(product_variant_id, quantity, warehouse_id)
                            VALUES(%s, %s, %s)
                        ON CONFLICT (warehouse_id, product_variant_id)
                        DO
                            UPDATE SET quantity = %s
                        """, (variant.id, v.loc['Quantity'], self.warehouse_id,
                              v.loc['Quantity']))


                except Exception as e:
                    error(f'Cannot upsert Variant Inventory for "{variant.name}".')
                    error(e)
                    return False

                # Insert options
                for (opt_name_header, opt_value_header) in Saleor.OPTION_HEADERS:
                    opt_attribute = v.loc[opt_name_header]
                    opt_value = v.loc[opt_value_header]

                    if has_value(opt_attribute) and has_value(opt_value):
                        opt_attribute = str(opt_attribute).strip()
                        opt_value = str(opt_value).strip()

                        ptype = next((p for p in self.product_types if
                                      p.type == row[Saleor.TYPE_KEY].strip()), None)

                        if ptype is not None:
                            attribute = next((a for a in ptype.variant_attributes if
                                              a.type == opt_attribute), None)

                            if attribute is not None:
                                attribute_value = next((v for v in attribute.values if
                                                        v.value == opt_value), None)

                                if attribute_value is not None:
                                    # product_assignedvariantattribute - variant_id: variant.id, assignment_id: product_attributevariant.id (where product.type_id and attribute.id)
                                    # product_assignedvariantattribute_values - assignedvariantattribute_id: id from previous, attributevalue_id: product_attributevalue.id

                                    assignment_id = \
                                        self.attribute_assignments[ptype.id][
                                            attribute.id]
                                    try:
                                        cursor.execute("""
                                            SELECT id
                                            FROM product_assignedvariantattribute
                                            WHERE variant_id = %s AND assignment_id = %s
                                            LIMIT 1""", (variant.id, assignment_id))

                                        result = cursor.fetchone()
                                        if result is None:
                                            # Assign variant attribute
                                            cursor.execute("""
                                                INSERT INTO product_assignedvariantattribute(variant_id, assignment_id)
                                                VALUES(%s, %s)
                                                ON CONFLICT (variant_id, assignment_id) DO NOTHING
                                                RETURNING id
                                            """, (variant.id, assignment_id))

                                            assignedvariantattribute_id = \
                                                cursor.fetchone()[0]
                                        else:
                                            assignedvariantattribute_id = result[0]
                                    except Exception as e:
                                        error(
                                            f'Cannot upsert Assigned Variant Attribute "{variant.id}:{assignment_id}".')
                                        error(e)
                                        return False

                                    try:
                                        cursor.execute("""
                                            INSERT INTO product_assignedvariantattribute_values
                                                (assignedvariantattribute_id, attributevalue_id)
                                            VALUES(%s, %s)
                                            ON CONFLICT (assignedvariantattribute_id, attributevalue_id) DO NOTHING
                                            RETURNING id
                                        """, (assignedvariantattribute_id,
                                              attribute_value.id))

                                    except Exception as e:
                                        error(
                                            f'Cannot upsert Assigned Variant Attribute Values' +
                                            f'"{assignedvariantattribute_id}:{attribute_value.id}".')
                                        error(e)
                                        return False

                                else:
                                    error(
                                        f'Cannot find attribute value "{opt_attribute}:{opt_value}" for variant {variant.name} ({variant.id})')
                                    return False
                            else:
                                error(
                                    f'Cannot find attribute "{opt_attribute}" for variant {variant.name} ({variant.id})')
                                return False
                        else:
                            error(
                                f'Cannot find product type for variant {variant.name} ({variant.id})')
                            return False

        return True

    def upload_images(self, df, photo_host):
        info(f"Uploading images from {photo_host}")
        photo_output = '../../media/products'

        if self.environment == 'local' and not os.path.exists(photo_output):
            os.makedirs(photo_output)

        # Proceed with the import
        cursor = self.db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        for (idx, v) in df.iterrows():
            sku = str(v.loc[Saleor.IMPORT_SKU]).lower().strip("'")

            # Find the SKU in db
            try:
                cursor.execute("""
                SELECT id, product_id FROM product_productvariant
                WHERE LOWER(sku) = %s
                LIMIT 1
                """, (sku,))

                result = cursor.fetchone()
                if result:
                    product_id = result['product_id']
                    variant_id = result['id']
                else:
                    warning(f'SKU "{sku}" not found in variant database.')
                    continue

            except Exception as e:
                warning(f'Could not fetch SKU "{sku}" in variant database.')
                continue

            # Seems okay, lets add the images
            variant_images = [v.loc[d] for d in Saleor.IMAGES if has_value(v.loc[d])]

            s3 = None
            AWS_MEDIA_BUCKET_NAME = os.environ.get("AWS_MEDIA_BUCKET_NAME")
            AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
            AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")

            if self.environment == 'production':
                session = boto3.Session(
                    aws_access_key_id=AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                )
                s3 = session.resource('s3')

            for img in variant_images:
                # if img not in filename_map.keys():
                #     warning(f'{img} missing from filename_map, skipping ({product_id}:{variant_id}).')
                #     continue

                try:
                    if self.environment == 'local':
                        dest = f'{photo_output}/{img}'
                        urllib.request.urlretrieve(
                            f'{photo_host}/{img.replace(" ", "%20")}', dest)
                    else:
                        fp = urllib.request.urlopen(
                            f'{photo_host}/{img.replace(" ", "%20")}')
                        img_bytes = fp.read()
                        s3.Bucket(AWS_MEDIA_BUCKET_NAME).put_object(
                            Body=img_bytes,
                            Key=f'products/{img}')

                    # Create product photo
                    cursor.execute("""
                        INSERT INTO product_productimage(image, ppoi, product_id, alt)
                        VALUES(%s, %s, %s, %s)
                        RETURNING id
                    """, (f'products/{img}', '0.5x0.5', product_id, ''))

                    img_id = cursor.fetchone()['id']

                    # Add to variant
                    cursor.execute("""
                        INSERT INTO product_variantimage(image_id, variant_id)
                        VALUES(%s, %s)
                        ON CONFLICT (image_id, variant_id) DO NOTHING
                    """, (img_id, variant_id))

                except Exception as e:
                    error(f'Cannot upload file "{img}" ({product_id}:{variant_id}).')
                    warning(img)
                    error(e)

        return True

    def make_description_block(self, text=''):
        letters = string.ascii_lowercase
        key = ''.join(random.choice(letters) for _ in range(5))

        return f"""
            {{"blocks": [{{"key": "{key}", "data": {{}}, "text": "{text}", "type": "unstyled", "depth": 0, "entityRanges": [], "inlineStyleRanges": []}}], "entityMap": {{}}}}
        """.strip()
