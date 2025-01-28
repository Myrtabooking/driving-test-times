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

def extract_available_times(driver, location_data):
    try:
        week_starting = driver.find_element(By.XPATH, "//span[@class='title']").text
        print(f"Week starting: {week_starting}")

        days = driver.find_elements(By.XPATH, "//span[@class='d']")
        day_dates = [day.text for day in days]

        times_by_day = {day: [] for day in day_dates}

        for day_index, day in enumerate(day_dates):
            available_times = driver.find_elements(
                By.XPATH, 
                f"//td[contains(@class, 'rms_{day[:3].lower()}')]//a[contains(@class, 'available')]"
            )
            for time_slot in available_times:
                times_by_day[day].append(time_slot.text)

        for day, times in times_by_day.items():
            if times:
                location_data[day] = times
                print(f"{day}: {', '.join(times)}")
    except Exception as e:
        print(f"Error extracting times: {e}")

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
        license_number = wait.until(EC.visibility_of_element_located((By.ID, "widget_cardNumber")))
        license_number.send_keys(os.environ['LICENSE_NUMBER'])

        password = wait.until(EC.visibility_of_element_located((By.ID, "widget_password")))
        password.send_keys(os.environ['PASSWORD'])

        print("Clicking login button...")
        login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[@id='nextButton_label']")))
        login_button.click()

        print("Navigating to book test page...")
        book_test_button = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//a[@class='general-btn' and contains(@href, 'tbsloginredirect')]")
        ))
        book_test_button.click()

        print("Selecting car test type...")
        car_radio_button = wait.until(EC.element_to_be_clickable((By.ID, "CAR")))
        driver.execute_script("arguments[0].click();", car_radio_button)

        print("Selecting driving test...")
        dt_radio_button = wait.until(EC.element_to_be_clickable((By.ID, "c1tt3")))
        driver.execute_script("arguments[0].click();", dt_radio_button)

        print("Proceeding to next step...")
        next_button = wait.until(EC.element_to_be_clickable((By.ID, "nextButton")))
        next_button.click()

        print("Accepting terms...")
        terms_checkbox = wait.until(EC.element_to_be_clickable((By.ID, "checkTerms")))
        terms_checkbox.click()

        next_button = wait.until(EC.element_to_be_clickable((By.ID, "nextButton")))
        next_button.click()

        print("Selecting location...")
        location_radio_button = driver.find_element(By.ID, "rms_batLocLocSel")
        if not location_radio_button.is_selected():
            location_radio_button.click()

        all_locations_data = {}

        while True:
            location_dropdown = wait.until(EC.presence_of_element_located((By.ID, "rms_batLocationSelect2")))
            select = Select(location_dropdown)
            location_options = select.options

            location_names = [
                option.text.strip() 
                for option in location_options 
                if option.text.strip().lower() != "choose..." and option.is_enabled()
            ]

            print(f"Found {len(location_names)} locations to process.")
            print("Locations:", ", ".join(location_names))

            for location_name in location_names:
                try:
                    print(f"\nProcessing location: {location_name}")
                    location_dropdown = wait.until(EC.presence_of_element_located((By.ID, "rms_batLocationSelect2")))
                    select = Select(location_dropdown)
                    select.select_by_visible_text(location_name)

                    next_button = wait.until(EC.element_to_be_clickable((By.ID, "nextButton")))
                    next_button.click()

                    time.sleep(1.5)

                    no_timeslot_weeks = 0
                    location_data = {}

                    while True:
                        extract_available_times(driver, location_data)

                        try:
                            alert_dialog = driver.find_element(By.XPATH, "//div[@role='alertdialog']")
                            alert_text = alert_dialog.text
                            if "There are no timeslots available for this week." in alert_text or "There are no timeslots available at this location." in alert_text:
                                no_timeslot_weeks += 1
                                print(f"No timeslots for week. Consecutive weeks with no slots: {no_timeslot_weeks}")
                                if no_timeslot_weeks >= 1:
                                    print("Stopping search for this location after consecutive weeks with no slots.")
                                    break
                        except:
                            no_timeslot_weeks = 0

                        try:
                            next_week_button = wait.until(EC.element_to_be_clickable((By.ID, "nextWeekButton")))
                            next_week_button.click()
                            time.sleep(1)
                        except:
                            print("No more weeks available or 'Next week' button not found.")
                            break

                    all_locations_data[location_name] = location_data

                    try:
                        back_to_locations_link = wait.until(EC.element_to_be_clickable((By.ID, "anotherLocationLink")))
                        back_to_locations_link.click()
                        time.sleep(2)
                    except:
                        print("Failed to navigate back to location selection.")
                        break

                except Exception as e:
                    print(f"An error occurred while processing location '{location_name}': {e}")
                    continue

            break

        print("\nScraping completed. Summary of results:")
        for location, data in all_locations_data.items():
            print(f"\nData for {location}:")
            for day, times in data.items():
                print(f"  {day}: {', '.join(times)}")

        print("\nSaving data to JSON file...")
        with open('data.json', 'w') as f:
            json.dump(all_locations_data, f, indent=4)
        print("Data has been saved to data.json")

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
