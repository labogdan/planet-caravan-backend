import sys
import os
from dotenv import load_dotenv

from Lib.CLI import *
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from time import sleep


def build_cache(arguments = None):
    environment = 'production'
    if '--local' in arguments:
        environment = 'local'
        load_dotenv()

    # Open up a browser
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--window-size=1920,1080")

    if environment == 'local':
        browser = webdriver.Chrome(options=chrome_options)
    else:
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")

        browser = webdriver.Chrome(
            executable_path=os.environ.get("CHROMEDRIVER_PATH"),
            options=chrome_options)


    # MAX_WAIT = 3 * 60
    # FILTER_SIDEBAR = '//div[@data-test="filterSidebar"]//span[contains(text(), "FILTERS")]'
    WAIT_TIME = 20
    # pages = [
    #     {
    #         'url': 'https://planet-caravan-storefront.herokuapp.com/category/headies/1/',
    #         # 'wait_for': FILTER_SIDEBAR
    #     },
    #     {
    #         'url': 'https://planet-caravan-storefront.herokuapp.com/category/smoke-shop/551/',
    #         # 'wait_for': FILTER_SIDEBAR
    #     }
    # ]

    urls = """https://planet-caravan-storefront.herokuapp.com/category/headies/1/
https://planet-caravan-storefront.herokuapp.com/category/caps/530/
https://planet-caravan-storefront.herokuapp.com/category/functional-pipes/26/
https://planet-caravan-storefront.herokuapp.com/category/mats/3314/
https://planet-caravan-storefront.herokuapp.com/category/merch/2/
https://planet-caravan-storefront.herokuapp.com/category/pearls/110/
https://planet-caravan-storefront.herokuapp.com/category/pendants-and-beads/48/
https://planet-caravan-storefront.herokuapp.com/category/quartz/478/
https://planet-caravan-storefront.herokuapp.com/category/slides/102/
https://planet-caravan-storefront.herokuapp.com/category/terp-slurper-accessories/344/
https://planet-caravan-storefront.herokuapp.com/category/tools-and-accessories/2430/
https://planet-caravan-storefront.herokuapp.com/category/smoke-shop/551/
https://planet-caravan-storefront.herokuapp.com/category/acrylic-pipes/800/
https://planet-caravan-storefront.herokuapp.com/category/air-freshener/2368/
https://planet-caravan-storefront.herokuapp.com/category/can-safes/2332/
https://planet-caravan-storefront.herokuapp.com/category/cleaners/2304/
https://planet-caravan-storefront.herokuapp.com/category/dab-supplies/2176/
https://planet-caravan-storefront.herokuapp.com/category/glass-waterpipes/832/
https://planet-caravan-storefront.herokuapp.com/category/grinders/1982/
https://planet-caravan-storefront.herokuapp.com/category/hand-pipes/558/
https://planet-caravan-storefront.herokuapp.com/category/papers/11036/
https://planet-caravan-storefront.herokuapp.com/category/quartz/478/
https://planet-caravan-storefront.herokuapp.com/category/rolling-supplies/1706/
https://planet-caravan-storefront.herokuapp.com/category/rolling-trays/1166/
https://planet-caravan-storefront.herokuapp.com/category/scales/1742/
https://planet-caravan-storefront.herokuapp.com/category/silicone-pipes/1612/
https://planet-caravan-storefront.herokuapp.com/category/storage/1082/
https://planet-caravan-storefront.herokuapp.com/category/tapestries/1376/
https://planet-caravan-storefront.herokuapp.com/category/headies/1/?sortBy=price
https://planet-caravan-storefront.herokuapp.com/category/caps/530/?sortBy=price
https://planet-caravan-storefront.herokuapp.com/category/functional-pipes/26/?sortBy=price
https://planet-caravan-storefront.herokuapp.com/category/mats/3314/?sortBy=price
https://planet-caravan-storefront.herokuapp.com/category/merch/2/?sortBy=price
https://planet-caravan-storefront.herokuapp.com/category/pearls/110/?sortBy=price
https://planet-caravan-storefront.herokuapp.com/category/pendants-and-beads/48/?sortBy=price
https://planet-caravan-storefront.herokuapp.com/category/quartz/478/?sortBy=price
https://planet-caravan-storefront.herokuapp.com/category/slides/102/?sortBy=price
https://planet-caravan-storefront.herokuapp.com/category/terp-slurper-accessories/344/?sortBy=price
https://planet-caravan-storefront.herokuapp.com/category/tools-and-accessories/2430/?sortBy=price
https://planet-caravan-storefront.herokuapp.com/category/smoke-shop/551/?sortBy=price
https://planet-caravan-storefront.herokuapp.com/category/acrylic-pipes/800/?sortBy=price
https://planet-caravan-storefront.herokuapp.com/category/air-freshener/2368/?sortBy=price
https://planet-caravan-storefront.herokuapp.com/category/can-safes/2332/?sortBy=price
https://planet-caravan-storefront.herokuapp.com/category/cleaners/2304/?sortBy=price
https://planet-caravan-storefront.herokuapp.com/category/dab-supplies/2176/?sortBy=price
https://planet-caravan-storefront.herokuapp.com/category/glass-waterpipes/832/?sortBy=price
https://planet-caravan-storefront.herokuapp.com/category/grinders/1982/?sortBy=price
https://planet-caravan-storefront.herokuapp.com/category/hand-pipes/558/?sortBy=price
https://planet-caravan-storefront.herokuapp.com/category/papers/11036/?sortBy=price
https://planet-caravan-storefront.herokuapp.com/category/quartz/478/?sortBy=price
https://planet-caravan-storefront.herokuapp.com/category/rolling-supplies/1706/?sortBy=price
https://planet-caravan-storefront.herokuapp.com/category/rolling-trays/1166/?sortBy=price
https://planet-caravan-storefront.herokuapp.com/category/scales/1742/?sortBy=price
https://planet-caravan-storefront.herokuapp.com/category/silicone-pipes/1612/?sortBy=price
https://planet-caravan-storefront.herokuapp.com/category/storage/1082/?sortBy=price
https://planet-caravan-storefront.herokuapp.com/category/tapestries/1376/?sortBy=price
https://planet-caravan-storefront.herokuapp.com/category/headies/1/?sortBy=-price
https://planet-caravan-storefront.herokuapp.com/category/caps/530/?sortBy=-price
https://planet-caravan-storefront.herokuapp.com/category/functional-pipes/26/?sortBy=-price
https://planet-caravan-storefront.herokuapp.com/category/mats/3314/?sortBy=-price
https://planet-caravan-storefront.herokuapp.com/category/merch/2/?sortBy=-price
https://planet-caravan-storefront.herokuapp.com/category/pearls/110/?sortBy=-price
https://planet-caravan-storefront.herokuapp.com/category/pendants-and-beads/48/?sortBy=-price
https://planet-caravan-storefront.herokuapp.com/category/quartz/478/?sortBy=-price
https://planet-caravan-storefront.herokuapp.com/category/slides/102/?sortBy=-price
https://planet-caravan-storefront.herokuapp.com/category/terp-slurper-accessories/344/?sortBy=-price
https://planet-caravan-storefront.herokuapp.com/category/tools-and-accessories/2430/?sortBy=-price
https://planet-caravan-storefront.herokuapp.com/category/smoke-shop/551/?sortBy=-price
https://planet-caravan-storefront.herokuapp.com/category/acrylic-pipes/800/?sortBy=-price
https://planet-caravan-storefront.herokuapp.com/category/air-freshener/2368/?sortBy=-price
https://planet-caravan-storefront.herokuapp.com/category/can-safes/2332/?sortBy=-price
https://planet-caravan-storefront.herokuapp.com/category/cleaners/2304/?sortBy=-price
https://planet-caravan-storefront.herokuapp.com/category/dab-supplies/2176/?sortBy=-price
https://planet-caravan-storefront.herokuapp.com/category/glass-waterpipes/832/?sortBy=-price
https://planet-caravan-storefront.herokuapp.com/category/grinders/1982/?sortBy=-price
https://planet-caravan-storefront.herokuapp.com/category/hand-pipes/558/?sortBy=-price
https://planet-caravan-storefront.herokuapp.com/category/papers/11036/?sortBy=-price
https://planet-caravan-storefront.herokuapp.com/category/quartz/478/?sortBy=-price
https://planet-caravan-storefront.herokuapp.com/category/rolling-supplies/1706/?sortBy=-price
https://planet-caravan-storefront.herokuapp.com/category/rolling-trays/1166/?sortBy=-price
https://planet-caravan-storefront.herokuapp.com/category/scales/1742/?sortBy=-price
https://planet-caravan-storefront.herokuapp.com/category/silicone-pipes/1612/?sortBy=-price
https://planet-caravan-storefront.herokuapp.com/category/storage/1082/?sortBy=-price
https://planet-caravan-storefront.herokuapp.com/category/tapestries/1376/?sortBy=-price
https://planet-caravan-storefront.herokuapp.com/category/headies/1/?sortBy=name
https://planet-caravan-storefront.herokuapp.com/category/caps/530/?sortBy=name
https://planet-caravan-storefront.herokuapp.com/category/functional-pipes/26/?sortBy=name
https://planet-caravan-storefront.herokuapp.com/category/mats/3314/?sortBy=name
https://planet-caravan-storefront.herokuapp.com/category/merch/2/?sortBy=name
https://planet-caravan-storefront.herokuapp.com/category/pearls/110/?sortBy=name
https://planet-caravan-storefront.herokuapp.com/category/pendants-and-beads/48/?sortBy=name
https://planet-caravan-storefront.herokuapp.com/category/quartz/478/?sortBy=name
https://planet-caravan-storefront.herokuapp.com/category/slides/102/?sortBy=name
https://planet-caravan-storefront.herokuapp.com/category/terp-slurper-accessories/344/?sortBy=name
https://planet-caravan-storefront.herokuapp.com/category/tools-and-accessories/2430/?sortBy=name
https://planet-caravan-storefront.herokuapp.com/category/smoke-shop/551/?sortBy=name
https://planet-caravan-storefront.herokuapp.com/category/acrylic-pipes/800/?sortBy=name
https://planet-caravan-storefront.herokuapp.com/category/air-freshener/2368/?sortBy=name
https://planet-caravan-storefront.herokuapp.com/category/can-safes/2332/?sortBy=name
https://planet-caravan-storefront.herokuapp.com/category/cleaners/2304/?sortBy=name
https://planet-caravan-storefront.herokuapp.com/category/dab-supplies/2176/?sortBy=name
https://planet-caravan-storefront.herokuapp.com/category/glass-waterpipes/832/?sortBy=name
https://planet-caravan-storefront.herokuapp.com/category/grinders/1982/?sortBy=name
https://planet-caravan-storefront.herokuapp.com/category/hand-pipes/558/?sortBy=name
https://planet-caravan-storefront.herokuapp.com/category/papers/11036/?sortBy=name
https://planet-caravan-storefront.herokuapp.com/category/quartz/478/?sortBy=name
https://planet-caravan-storefront.herokuapp.com/category/rolling-supplies/1706/?sortBy=name
https://planet-caravan-storefront.herokuapp.com/category/rolling-trays/1166/?sortBy=name
https://planet-caravan-storefront.herokuapp.com/category/scales/1742/?sortBy=name
https://planet-caravan-storefront.herokuapp.com/category/silicone-pipes/1612/?sortBy=name
https://planet-caravan-storefront.herokuapp.com/category/storage/1082/?sortBy=name
https://planet-caravan-storefront.herokuapp.com/category/tapestries/1376/?sortBy=name
https://planet-caravan-storefront.herokuapp.com/category/headies/1/?sortBy=-name
https://planet-caravan-storefront.herokuapp.com/category/caps/530/?sortBy=-name
https://planet-caravan-storefront.herokuapp.com/category/functional-pipes/26/?sortBy=-name
https://planet-caravan-storefront.herokuapp.com/category/mats/3314/?sortBy=-name
https://planet-caravan-storefront.herokuapp.com/category/merch/2/?sortBy=-name
https://planet-caravan-storefront.herokuapp.com/category/pearls/110/?sortBy=-name
https://planet-caravan-storefront.herokuapp.com/category/pendants-and-beads/48/?sortBy=-name
https://planet-caravan-storefront.herokuapp.com/category/quartz/478/?sortBy=-name
https://planet-caravan-storefront.herokuapp.com/category/slides/102/?sortBy=-name
https://planet-caravan-storefront.herokuapp.com/category/terp-slurper-accessories/344/?sortBy=-name
https://planet-caravan-storefront.herokuapp.com/category/tools-and-accessories/2430/?sortBy=-name
https://planet-caravan-storefront.herokuapp.com/category/smoke-shop/551/?sortBy=-name
https://planet-caravan-storefront.herokuapp.com/category/acrylic-pipes/800/?sortBy=-name
https://planet-caravan-storefront.herokuapp.com/category/air-freshener/2368/?sortBy=-name
https://planet-caravan-storefront.herokuapp.com/category/can-safes/2332/?sortBy=-name
https://planet-caravan-storefront.herokuapp.com/category/cleaners/2304/?sortBy=-name
https://planet-caravan-storefront.herokuapp.com/category/dab-supplies/2176/?sortBy=-name
https://planet-caravan-storefront.herokuapp.com/category/glass-waterpipes/832/?sortBy=-name
https://planet-caravan-storefront.herokuapp.com/category/grinders/1982/?sortBy=-name
https://planet-caravan-storefront.herokuapp.com/category/hand-pipes/558/?sortBy=-name
https://planet-caravan-storefront.herokuapp.com/category/papers/11036/?sortBy=-name
https://planet-caravan-storefront.herokuapp.com/category/quartz/478/?sortBy=-name
https://planet-caravan-storefront.herokuapp.com/category/rolling-supplies/1706/?sortBy=-name
https://planet-caravan-storefront.herokuapp.com/category/rolling-trays/1166/?sortBy=-name
https://planet-caravan-storefront.herokuapp.com/category/scales/1742/?sortBy=-name
https://planet-caravan-storefront.herokuapp.com/category/silicone-pipes/1612/?sortBy=-name
https://planet-caravan-storefront.herokuapp.com/category/storage/1082/?sortBy=-name
https://planet-caravan-storefront.herokuapp.com/category/tapestries/1376/?sortBy=-name
https://planet-caravan-storefront.herokuapp.com/category/headies/1/?sortBy=-updated_at
https://planet-caravan-storefront.herokuapp.com/category/caps/530/?sortBy=-updated_at
https://planet-caravan-storefront.herokuapp.com/category/functional-pipes/26/?sortBy=-updated_at
https://planet-caravan-storefront.herokuapp.com/category/mats/3314/?sortBy=-updated_at
https://planet-caravan-storefront.herokuapp.com/category/merch/2/?sortBy=-updated_at
https://planet-caravan-storefront.herokuapp.com/category/pearls/110/?sortBy=-updated_at
https://planet-caravan-storefront.herokuapp.com/category/pendants-and-beads/48/?sortBy=-updated_at
https://planet-caravan-storefront.herokuapp.com/category/quartz/478/?sortBy=-updated_at
https://planet-caravan-storefront.herokuapp.com/category/slides/102/?sortBy=-updated_at
https://planet-caravan-storefront.herokuapp.com/category/terp-slurper-accessories/344/?sortBy=-updated_at
https://planet-caravan-storefront.herokuapp.com/category/tools-and-accessories/2430/?sortBy=-updated_at
https://planet-caravan-storefront.herokuapp.com/category/smoke-shop/551/?sortBy=-updated_at
https://planet-caravan-storefront.herokuapp.com/category/acrylic-pipes/800/?sortBy=-updated_at
https://planet-caravan-storefront.herokuapp.com/category/air-freshener/2368/?sortBy=-updated_at
https://planet-caravan-storefront.herokuapp.com/category/can-safes/2332/?sortBy=-updated_at
https://planet-caravan-storefront.herokuapp.com/category/cleaners/2304/?sortBy=-updated_at
https://planet-caravan-storefront.herokuapp.com/category/dab-supplies/2176/?sortBy=-updated_at
https://planet-caravan-storefront.herokuapp.com/category/glass-waterpipes/832/?sortBy=-updated_at
https://planet-caravan-storefront.herokuapp.com/category/grinders/1982/?sortBy=-updated_at
https://planet-caravan-storefront.herokuapp.com/category/hand-pipes/558/?sortBy=-updated_at
https://planet-caravan-storefront.herokuapp.com/category/papers/11036/?sortBy=-updated_at
https://planet-caravan-storefront.herokuapp.com/category/quartz/478/?sortBy=-updated_at
https://planet-caravan-storefront.herokuapp.com/category/rolling-supplies/1706/?sortBy=-updated_at
https://planet-caravan-storefront.herokuapp.com/category/rolling-trays/1166/?sortBy=-updated_at
https://planet-caravan-storefront.herokuapp.com/category/scales/1742/?sortBy=-updated_at
https://planet-caravan-storefront.herokuapp.com/category/silicone-pipes/1612/?sortBy=-updated_at
https://planet-caravan-storefront.herokuapp.com/category/storage/1082/?sortBy=-updated_at
https://planet-caravan-storefront.herokuapp.com/category/tapestries/1376/?sortBy=-updated_at
"""

    # for page in pages:
    #     info(f'Fetching {page["url"]}')
    #     browser.get(page['url'])
    #     info(f"Waiting {WAIT_TIME}")
    #     sleep(WAIT_TIME)
    for url in urls.split('\n'):
        info(f'Fetching {url}')
        browser.get(url)
        info(f"Waiting {WAIT_TIME}")
        sleep(WAIT_TIME)
        # info(f'Waiting for {page["wait_for"]}')

        # try:
        #     wait_for_element(browser, page['wait_for'], MAX_WAIT)
        # except:
        #     error("Timeout: Couldn't find element.")


    comment("")
    comment("Done")

# def wait_for_element(browser, xpath, max_time=10):
#     attempts = 0
#
#     while attempts < 5:
#         try:
#             element_present = EC.presence_of_element_located((By.XPATH, xpath))
#             WebDriverWait(browser, max_time).until(element_present)
#             return browser.find_element_by_xpath(xpath)
#
#         except:
#             attempts += 1
#     raise Exception(f'Could not wait for element: {xpath} (Attempted {attempts} times).')

if __name__ == '__main__':
    build_cache(sys.argv)
