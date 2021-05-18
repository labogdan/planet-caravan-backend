import os
import sys
from dotenv import load_dotenv
from Lib.CLI import *
import psycopg2
from psycopg2.extras import DictCursor
import subprocess
import traceback

def eq_border(s = ''):
    return "=".join(["" for _ in range(len(s) + 1)])

def get_command(cmd_type = ''):
    cmds = {
        'zoho': 'python scripts/planet-caravan/zoho-sync.py',
        'inventory-pricing': 'python scripts/planet-caravan/stock-sync.py',
        'orders': 'python scripts/planet-caravan/adjust-inventory.py',
        'algolia': 'python scripts/algolia/sync.py'
    }

    if cmd_type in cmds.keys():
        return cmds[cmd_type]
    return None



def run_queue(arguments = None):
    t = '== Running Queue =='
    info(eq_border(t))
    info(t)
    info(eq_border(t))

    env = 'production'

    if '--local' in arguments:
        env = 'local'
        load_dotenv()

    db = db_connect(env)
    cursor = db.cursor(cursor_factory=DictCursor)

    cursor.execute("""
        SELECT *
        FROM sync_queuejob
        WHERE status = 0 AND started_at IS NULL and completed_at IS NULL
    """)

    # Aggregate all commands so they aren't run 20 times in a row
    commands = {}
    for result in cursor.fetchall():
        cmd = result['command_type']
        if cmd not in commands.keys():
            commands[cmd] = []
        commands[cmd].append(result['id'])

    if not len(commands.keys()):
        # Fail fast
        warning("Nothing in queue.")
        return

    for cmd_type, cmd_ids in commands.items():
        print('')
        ct = f'== Running `{cmd_type}` =='
        warning(eq_border(ct))
        warning(ct)
        warning(eq_border(ct))

        # Set as started
        cursor.execute("""
            UPDATE sync_queuejob
            SET started_at = NOW()
            WHERE id in %s
            """, (tuple(cmd_ids),))

        cmd = get_command(cmd_type)

        if not cmd:
            # Non-existent command, update these as failed and completed
            cursor.execute("""
                UPDATE sync_queuejob
                SET status = 0, completed_at = NOW()
                WHERE id in %s
                """, (tuple(cmd_ids),))
            continue

        # Should be good to actually run the command now
        try:
            # Show the command, run it, and update the db
            comment(cmd)
            subprocess.check_output(cmd, shell=True, stderr=subprocess.PIPE)
            cursor.execute("""
                UPDATE sync_queuejob
                SET status = 1, completed_at = NOW()
                WHERE id in %s
                """, (tuple(cmd_ids),))
        except subprocess.CalledProcessError as e:
            # Log the error generated from the subprocess
            output = str((e.output if e.output else e.stderr).decode('utf-8'))
            cursor.execute("""
                UPDATE sync_queuejob
                SET status = 0, completed_at = NOW(), output = %s
                WHERE id in %s
                """, (output, tuple(cmd_ids)))
        except:
            # Something failed in this script
            output = str(traceback.format_exc())
            cursor.execute("""
                UPDATE sync_queuejob
                SET status = 0, completed_at = NOW(), output = %s
                WHERE id in %s
                """, (output, tuple(cmd_ids)))

def db_connect(env='production'):
    comment("Connecting to DB")

    try:
        if env == 'local':
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

if __name__ == '__main__':
    run_queue(sys.argv)
    comment('')
    comment('Done.')
