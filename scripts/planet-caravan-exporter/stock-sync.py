from dotenv import load_dotenv

from Lib.Saleor.Saleor import Saleor
from Lib.ShopKeep.ShopKeep import ShopKeep


def run_process():
    sk = ShopKeep()
    stock_file = sk.run()

    print(stock_file)

    s = Saleor()
    s.update_stock(stock_file)



if __name__ == '__main__':
    run_process()
