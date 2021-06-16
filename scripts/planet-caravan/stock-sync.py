import sys
from dotenv import load_dotenv

from Lib.Saleor.Saleor import Saleor
from Lib.ShopKeep.ShopKeepToSaleor import ShopKeepToSaleor
from Lib.Email import send_email


def run_process(arguments = None):
    environment = 'production'
    if '--local' in arguments:
        environment = 'local'
        load_dotenv()

    sk = ShopKeepToSaleor(environment)
    stock_file = sk.run()

    s = Saleor(environment)
    result = s.update_stock(stock_file)

    # Try sending email
    try:
        send_email('ShopKeep Stock Sync complete', 'Complete.')
    except:
        pass



    return result


if __name__ == '__main__':
    run_process(sys.argv)
