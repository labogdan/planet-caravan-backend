
import sys
import os
import subprocess
import traceback
# import pathlib
# # sys.path.append(f'{str(pathlib.Path(__file__).parent.parent.absolute())}/scripts')
# # p = f'{str(pathlib.Path(__file__).parent.parent.parent.absolute())}/scripts/planet_caravan'
# p = f'./scripts'
# # print(f'File: {str(pathlib.Path(__file__))}')
# # print(f'Path: {p}')
# if p not in sys.path:
#     sys.path.insert(0, p)
# from pprint import pprint
# pprint(sys.path)
#
# print(f'CWD: {os.getcwd()}')
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse, JsonResponse


# import importlib.util
# spec = importlib.util.spec_from_file_location("zoho_sync", f'{p}/zoho_sync.py')
# foo = importlib.util.module_from_spec(spec)
# spec.loader.exec_module(foo)
#
# print(f'TYPE: {type(foo.do_import)}')

# help("modules")

# import importlib.util
#
# spec = importlib.util.spec_from_file_location("zoho_sync",
#                                               f'{str(pathlib.Path(__file__).parent.parent.absolute())}/scripts/planet_caravan/zoho_sync.py')
# foo = importlib.util.module_from_spec(spec)
# spec.loader.exec_module(foo)
# # foo.MyClass()
# zoho_sync.do_import()

# pprint(sys.path)
# from scripts.planet_caravan.zoho_sync import do_import, fix_category_hierarchy, bust_cache
# from scripts.planet_caravan.stock_sync import run_process as inventory_sync
# from scripts.planet_caravan.adjust_inventory import run_process as order_sync


def handle_sync_url(request: WSGIRequest, sync_type: str) -> HttpResponse:
    cmd = None

    if sync_type == 'zoho':
        cmd = 'python scripts/planet-caravan/zoho-sync.py'
    elif sync_type == 'inventory-pricing':
        cmd = 'python scripts/planet-caravan/stock-sync.py'
    elif sync_type == 'orders':
        cmd = 'python scripts/planet-caravan/adjust-inventory.py'

    output = ''
    if cmd:
        try:
            output = subprocess.check_output(cmd, shell=True)
        except Exception as e:
            output = str(traceback.format_exc())
            pass

    return JsonResponse(
        data={'type': sync_type, 'output': output},
        status=200, )
