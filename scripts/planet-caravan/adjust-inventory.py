import sys
from dotenv import load_dotenv
from pprint import pprint
from Lib.Saleor.Saleor import Saleor
from Lib.ShopKeep.SaleorToShopKeep import SaleorToShopKeep


def run_process(arguments):
    environment = 'production'

    if len(arguments) >= 2 and arguments[1] == '--local':
        del arguments[1]
        environment = 'local'
        load_dotenv()


    s = Saleor(environment)
    s.db_connect()
    adjustments = s.get_adjustments()


    sk = SaleorToShopKeep(environment, adjustments)
    sk.run(s.mark_adjusted)


if __name__ == '__main__':
    run_process(sys.argv)
