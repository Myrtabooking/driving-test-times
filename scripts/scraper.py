import tempfile
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from fake_useragent import UserAgent
from fp.fp import FreeProxy
import time
import json
import os
import random

def get_working_proxy():
    try:
        proxy = FreeProxy(country_id=['US', 'CA', 'AU'], timeout=1).get()
        return proxy
    except:
        return None

def create_driver(retry_count=0):
    if retry_count >= 3:
        raise Exception("Failed to create a working driver after 3 attempts")

    try:
        chrome_options = Options()
        
        # Generate random user agent
        ua = UserAgent()
        user_agent = ua.random
        
        # Anti-detection measures
        chrome_options.add_argument(f'user-agent={user_agent}')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Required for GitHub Actions
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        # Additional options
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--start-maximized')
        
        # Try to get and use a proxy
        proxy = get_working_proxy()
        if proxy:
            chrome_options.add_argument(f'--proxy-server={proxy}')

        driver = webdriver.Chrome(options=chrome_options)
        
        # Additional anti-detection measures
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": user_agent})
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    except Exception as e:
        print(f"Failed to create driver: {str(e)}")
        return create_driver(retry_count + 1)

def try_access_site(driver, url, max_retries=3):
    for attempt in range(max_retries):
        try:
            driver.get(url)
            time.sleep(random.uniform(2, 4))  # Random delay
            
            if "Access Denied" in driver.title:
                print(f"Access denied on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    driver.quit()
                    driver = create_driver()
                    continue
            else:
                return True
        except Exception as e:
            print(f"Error on attempt {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                driver.quit()
                driver = create_driver()
                continue
    return False

def main():
    driver = create_driver()
    
    try:
        print("Starting the scraping process...")
        url = "https://www.myrta.com/wps/portal/extvp/myrta/login/"
        
        print("Attempting to access the website...")
        if not try_access_site(driver, url):
            raise Exception("Failed to access the site after multiple attempts")

        print("Successfully accessed the website")
        wait = WebDriverWait(driver, 20)

        print("Attempting to login...")
        # Your existing login and scraping code here
        license_number = wait.until(EC.visibility_of_element_located((By.ID, "widget_cardNumber")))
        license_number.send_keys(os.environ['LICENSE_NUMBER'])

        password = wait.until(EC.visibility_of_element_located((By.ID, "widget_password")))
        password.send_keys(os.environ['PASSWORD'])

        # Rest of your existing code...
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        if driver:
            print("\nCurrent URL:", driver.current_url)
            print("Page Title:", driver.title)
            print("\nPage source at time of error:")
            print(driver.page_source)
        raise
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()
