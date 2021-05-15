import sys
from dotenv import load_dotenv

from Lib.Saleor.Saleor import Saleor
from Lib.ShopKeep.ShopKeepToSaleor import ShopKeepToSaleor


def run_process(arguments = None):
    environment = 'production'
    if '--local' in arguments:
        environment = 'local'
        load_dotenv()

    sk = ShopKeepToSaleor(environment)
    stock_file = sk.run()

    s = Saleor(environment)
    return s.update_stock(stock_file)


if __name__ == '__main__':
    run_process(sys.argv)
