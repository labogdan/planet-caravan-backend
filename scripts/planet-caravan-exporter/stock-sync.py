from dotenv import load_dotenv

from Lib.Saleor.Saleor import Saleor
from Lib.ShopKeep.ShopKeep import ShopKeep


def run_process():
    load_dotenv()

    # sk = ShopKeep()
    # stock_file = sk.run()

    stock_file = '/Users/josh/Sites/Round Pixel Studio/planet-caravan-exporter/downloads/planetcaravan_stock_items.csv'

    s = Saleor()
    s.update_stock(stock_file)



if __name__ == '__main__':
    run_process()
