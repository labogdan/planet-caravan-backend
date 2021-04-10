import sys
from dotenv import load_dotenv
from Lib.CLI import *
from Lib.helpers import handleize
from Lib.Saleor.Saleor import Saleor
import os
import psycopg2
import psycopg2.extras
import pandas as pd
import json


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

    df = pd.read_csv(arguments[1], converters={**{k: str for k in ['SKU', 'Record Id']}})
    for (i, row) in df.iterrows():
        sku = str(row.loc['SKU']).strip("'")
        zoho_id = str(row.loc['Record Id']).strip("zcrm_")

        info(f'{sku} | {zoho_id}')

        cursor.execute("""
        UPDATE product_product p
            SET private_metadata = jsonb_set(p.private_metadata, '{ZOHO_ID}', %s, true)
            FROM product_productvariant pv
            WHERE p.id = pv.product_id AND pv.sku = %s
        """, (zoho_id, sku))

if __name__ == '__main__':
    fix_things(sys.argv)
