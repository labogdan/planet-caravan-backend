import sys
from dotenv import load_dotenv
from pprint import pprint
from Lib.Saleor.Saleor import Saleor
from Lib.ShopKeep.SaleorToShopKeep import SaleorToShopKeep
from pprint import pprint
from Lib.Email import send_email

def run_process(arguments = None):
    environment = 'production'

    if len(arguments) >= 2 and arguments[1] == '--local':
        del arguments[1]
        environment = 'local'
        load_dotenv()

    s = Saleor(environment)
    s.db_connect()
    adjustments = s.get_adjustments()

    if adjustments and len(adjustments.keys()) < 1:
        return

    sk = SaleorToShopKeep(environment, adjustments)
    result = sk.run(s.mark_adjusted)

    # Try sending email
    try:
        adj_count = len(adjustments.keys())
        adj = 'Adjustment' if adj_count == 1 else 'Adjustments'
        send_email('Order Adjustment Sync complete', f'{adj_count} {adj} made.')
    except:
        pass


    return result


if __name__ == '__main__':
    run_process(sys.argv)
