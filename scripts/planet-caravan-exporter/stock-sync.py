from dotenv import load_dotenv

from Lib.Saleor.Saleor import Saleor
from Lib.ShopKeep.ShopKeep import ShopKeep


def run_process():
    environment = 'production'
    if len(arguments) and arguments[1] == '--local':
        del arguments[1]
        environment = 'local'
        load_dotenv()

    sk = ShopKeep(environment)
    stock_file = sk.run()

    print(stock_file)

    s = Saleor(environment)
    s.update_stock(stock_file)


if __name__ == '__main__':
    run_process()
