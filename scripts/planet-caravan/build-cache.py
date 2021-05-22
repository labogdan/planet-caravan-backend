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
            chrome_options=chrome_options)


    # MAX_WAIT = 3 * 60
    # FILTER_SIDEBAR = '//div[@data-test="filterSidebar"]//span[contains(text(), "FILTERS")]'
    WAIT_TIME = 20
    pages = [
        {
            'url': 'https://planet-caravan-storefront.herokuapp.com/category/headies/1/',
            # 'wait_for': FILTER_SIDEBAR
        },
        {
            'url': 'https://planet-caravan-storefront.herokuapp.com/category/smoke-shop/551/',
            # 'wait_for': FILTER_SIDEBAR
        }
    ]

    for page in pages:
        info(f'Fetching {page["url"]}')
        browser.get(page['url'])
        info(f"Waiting {WAIT_TIME}")
        sleep(WAIT_TIME)
        # info(f'Waiting for {page["wait_for"]}')

        # try:
        #     wait_for_element(browser, page['wait_for'], MAX_WAIT)
        # except:
        #     error("Timeout: Couldn't find element.")


    comment("")
    comment("Done")
    while True:
        sleep(1)


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
