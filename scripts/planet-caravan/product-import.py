import sys
from dotenv import load_dotenv

from Lib.Saleor.Saleor import Saleor
# from Lib.ShopKeep.ShopKeepToSaleor import ShopKeepToSaleor


def run_process(arguments):

    print("Disabled in lieu of Zoho automation.")
    return
    #
    # environment = 'production'
    # if len(arguments) and arguments[1] == '--local':
    #     del arguments[1]
    #     environment = 'local'
    #     load_dotenv()
    #
    # s = Saleor(environment)
    # s.import_all(arguments[1], arguments[2])


if __name__ == '__main__':
    run_process(sys.argv)
