import os
from time import sleep
import traceback

from Lib.CLI import *
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager


class SaleorToShopKeep:
    def __init__(self, environment, adjustments, ):
        self.environment = environment
        self.timeout = int(os.getenv('SK_TIMEOUT'), 10)
        self.browser = None
        self.adjustments = adjustments

    def run(self, mark_adjusted=None):
        url = os.getenv('SK_HOSTNAME')
        chrome_version = os.getenv('CHROMEDRIVER_VERSION')

        # Open up a browser
        chrome_options = webdriver.ChromeOptions()
        preferences = {"directory_upgrade": True,
                       "safebrowsing.enabled": True}

        chrome_options.add_experimental_option("prefs", preferences)

        if self.environment != 'local':
            chrome_options.add_argument("--headless")

        chrome_options.add_argument("--window-size=1920,1080")

        if self.environment == 'local':
            self.browser = webdriver.Chrome(
                ChromeDriverManager(version=chrome_version).install(),
                options=chrome_options)
        else:
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--no-sandbox")
            # chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")

            self.browser = webdriver.Chrome(
                ChromeDriverManager(version=chrome_version).install(),
                chrome_options=chrome_options)

        self.browser.get(url)

        # Sequence of events
        self.login()
        self.navigate_to_adjustments()

        self.change_inventories(mark_adjusted)

        return True

    def get_main_frame(self):
        iframe_path = '//iframe[contains(@title, "iframe")]'
        self.wait_for_element(iframe_path)
        iframe = self.browser.find_element_by_xpath(iframe_path)
        self.browser.switch_to_frame(iframe)

    def login(self):
        print("Logging in...")

        store = os.getenv('SK_STORE')
        username = os.getenv('SK_USER')
        password = os.getenv('SK_PASSWORD')

        # Wait to load
        element_present = EC.presence_of_element_located((By.ID, 'backoffice-login'))
        WebDriverWait(self.browser, self.timeout).until(element_present)

        # Log in
        storename_field = self.browser.find_element_by_id('store_name')
        username_field = self.browser.find_element_by_id('login')
        password_field = self.browser.find_element_by_id('password')

        storename_field.send_keys(store)
        username_field.send_keys(username)
        password_field.send_keys(password)

        submit = self.browser.find_element_by_id('submit')

        submit.click()

    def wait_for_element(self, xpath, max_time=10):
        if not max_time:
            max_time = self.timeout

        element_present = EC.presence_of_element_located((By.XPATH, xpath))
        WebDriverWait(self.browser, max_time).until(element_present)

        return self.browser.find_element_by_xpath(xpath)

    def wait_then_click(self, xpath, max_time=10):
        element = self.wait_for_element(xpath, max_time)
        sleep(0.05)
        element.click()

    def navigate_to_adjustments(self):
        print("Navigating to adjustments page...")

        # Open the menu
        menu_xpath = '//*[contains(@class, "ls-bonfire-sidebar")]//a[contains(@data-test,"SidebarLink-1-Items")]'
        self.wait_then_click(menu_xpath)

        info('clicked')

        sleep(0.5)

        report_path = '//a[contains(@data-test, "SidebarLink-2-Adjust Inventory")]'
        self.wait_then_click(report_path)
        warning('clicked')

    def change_inventories(self, mark_adjusted):

        self.get_main_frame()

        for order_id, order in self.adjustments.items():
            info(f'Syncing Order #{order_id}')

            order_okay = True
            for item in order.values():
                try:
                    search_field_path = '//*[@id="item_input"]'
                    self.wait_for_element(search_field_path)
                    search_field = self.browser.find_element_by_id('item_input')

                    comment(f'Searching {item["search"]}')
                    search_field.send_keys(item['search'])

                    # Give the browser time to destroy/recreate the result dropdown
                    sleep(3)

                    dropdown_path = '//*[@id="ui-id-1"]'
                    # title = item['title']
                    # variant = item['variant'] if 'variant' in item else ''

                    # full_title = f'{title}{f" - {variant}" if variant else ""}'
                    first_result = f'{dropdown_path}/li/a[position() = 1]'
                    self.wait_then_click(first_result)

                    sleep(3)
                    qty_path = '//*[@id="quantity_input"]'
                    qty_input = self.wait_for_element(qty_path, self.timeout)

                    qty_input.send_keys(str(item['adjustment']))

                    submit_path = '//a[@id="add_to_count"]'
                    self.wait_then_click(submit_path, self.timeout)

                    sleep(1)
                except Exception as e:
                    error(e)
                    error(traceback.format_exc())
                    order_okay = False
                    sleep(1)

            mark_adjusted(order_id, 1 if order_okay else 0)
