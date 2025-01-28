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
        print(f"Using proxy: {proxy}")
        return proxy
    except Exception as e:
        print(f"Error getting proxy: {e}")
        return None

def setup_driver(retry_count=0):
    if retry_count >= 3:
        raise Exception("Failed to create a working driver after 3 attempts")

    try:
        chrome_options = Options()
        ua = UserAgent()
        user_agent = ua.random
        
        # Anti-detection measures
        chrome_options.add_argument(f'user-agent={user_agent}')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # GitHub Actions specific options
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        # Add proxy
        proxy = get_working_proxy()
        if proxy:
            chrome_options.add_argument(f'--proxy-server={proxy}')

        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    except Exception as e:
        print(f"Failed to create driver: {str(e)}")
        return setup_driver(retry_count + 1)

def try_access_site(driver, url, max_retries=3):
    for attempt in range(max_retries):
        try:
            driver.get(url)
            time.sleep(random.uniform(2, 4))  # Random delay
            
            if "Access Denied" in driver.title:
                print(f"Access denied on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    driver.quit()
                    driver = setup_driver()
                    continue
            else:
                return driver, True
        except Exception as e:
            print(f"Error on attempt {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                driver.quit()
                driver = setup_driver()
                continue
    return driver, False

def extract_times(driver, location_data):
    try:
        week_starting = driver.find_element(By.XPATH, "//span[@class='title']").text
        print(f"Week starting: {week_starting}")

        days = driver.find_elements(By.XPATH, "//span[@class='d']")
        day_dates = [day.text for day in days]

        for day in day_dates:
            available_times = driver.find_elements(
                By.XPATH, 
                f"//td[contains(@class, 'rms_{day[:3].lower()}')]//a[contains(@class, 'available')]"
            )
            times = [time_slot.text for time_slot in available_times]
            if times:
                location_data[day] = times
                print(f"{day}: {', '.join(times)}")
    except Exception as e:
        print(f"Error extracting times: {e}")

def main():
    driver = None
    try:
        print("Starting the scraping process...")
        driver = setup_driver()
        
        print("Attempting to access the website...")
        driver, success = try_access_site(driver, "https://www.myrta.com/wps/portal/extvp/myrta/login/")
        
        if not success:
            print("Failed to access the site after multiple attempts")
            return

        wait = WebDriverWait(driver, 20)
        print("Successfully accessed the website")

        print("Attempting login...")
        license_input = wait.until(EC.visibility_of_element_located((By.ID, "widget_cardNumber")))
        license_input.send_keys(os.environ['LICENSE_NUMBER'])

        password_input = wait.until(EC.visibility_of_element_located((By.ID, "widget_password")))
        password_input.send_keys(os.environ['PASSWORD'])

        login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[@id='nextButton_label']")))
        login_button.click()

        print("Navigating to booking page...")
        book_test = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//a[@class='general-btn' and contains(@href, 'tbsloginredirect')]")
        ))
        book_test.click()

        print("Selecting test type...")
        car_option = wait.until(EC.element_to_be_clickable((By.ID, "CAR")))
        driver.execute_script("arguments[0].click();", car_option)

        dt_option = wait.until(EC.element_to_be_clickable((By.ID, "c1tt3")))
        driver.execute_script("arguments[0].click();", dt_option)

        next_button = wait.until(EC.element_to_be_clickable((By.ID, "nextButton")))
        next_button.click()

        print("Accepting terms...")
        terms = wait.until(EC.element_to_be_clickable((By.ID, "checkTerms")))
        terms.click()

        next_button = wait.until(EC.element_to_be_clickable((By.ID, "nextButton")))
        next_button.click()

        print("Processing locations...")
        location_radio = driver.find_element(By.ID, "rms_batLocLocSel")
        if not location_radio.is_selected():
            location_radio.click()

        all_locations_data = {}

        location_dropdown = wait.until(EC.presence_of_element_located((By.ID, "rms_batLocationSelect2")))
        select = Select(location_dropdown)
        locations = [opt.text.strip() for opt in select.options if opt.text.strip().lower() != "choose..."]

        print(f"Found {len(locations)} locations to process")
        
        for location in locations:
            try:
                print(f"\nProcessing location: {location}")
                select = Select(driver.find_element(By.ID, "rms_batLocationSelect2"))
                select.select_by_visible_text(location)

                next_button = wait.until(EC.element_to_be_clickable((By.ID, "nextButton")))
                next_button.click()
                time.sleep(2)

                location_data = {}
                no_slots_count = 0

                while True:
                    extract_times(driver, location_data)

                    try:
                        alert = driver.find_element(By.XPATH, "//div[@role='alertdialog']")
                        if "no timeslots available" in alert.text.lower():
                            no_slots_count += 1
                            if no_slots_count >= 2:
                                print("No more slots available for this location")
                                break
                    except:
                        no_slots_count = 0

                    try:
                        next_week = wait.until(EC.element_to_be_clickable((By.ID, "nextWeekButton")))
                        next_week.click()
                        time.sleep(1)
                    except:
                        print("No more weeks available")
                        break

                if location_data:
                    all_locations_data[location] = location_data
                    print(f"Found {len(location_data)} days with available slots")

                print("Navigating back to location selection...")
                back_link = wait.until(EC.element_to_be_clickable((By.ID, "anotherLocationLink")))
                back_link.click()
                time.sleep(2)

            except Exception as e:
                print(f"Error processing location {location}: {e}")
                continue

        print("\nScraping completed. Summary of results:")
        for location, data in all_locations_data.items():
            print(f"\nData for {location}:")
            for day, times in data.items():
                print(f"  {day}: {', '.join(times)}")

        print("\nSaving results to JSON...")
        with open('data.json', 'w') as f:
            json.dump(all_locations_data, f, indent=4)
        print("Data saved successfully to data.json")

    except Exception as e:
        print(f"An error occurred: {e}")
        if driver:
            print(f"Current URL: {driver.current_url}")
            print(f"Page Title: {driver.title}")
            print("Page source:")
            print(driver.page_source)
    
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()
