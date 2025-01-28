import tempfile
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import json
import os

# Create a temporary directory for user data
user_data_dir = tempfile.mkdtemp()

chrome_options = Options()
chrome_options.add_argument(f"--user-data-dir={user_data_dir}")  # Set a unique user data directory
chrome_options.add_argument("--headless")  # Keep this if you want headless mode
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/103.0.5060.114 Safari/537.36")

driver = webdriver.Chrome(options=chrome_options)

try:
    driver.get("https://www.myrta.com/wps/portal/extvp/myrta/login/")
    wait = WebDriverWait(driver, 20)  # Increased wait time

    # Debugging: Print the page source to see if the page loaded correctly
    print(driver.page_source)

    # Check if the element is inside an iframe
    # If it is, switch to the iframe first
    # driver.switch_to.frame("frame_name_or_id")  # Uncomment and replace with actual frame name or ID if needed

    # Use environment variables for license number and password
    license_number = wait.until(EC.visibility_of_element_located((By.ID, "widget_cardNumber")))
    license_number.send_keys(os.environ['LICENSE_NUMBER'])

    password = wait.until(EC.visibility_of_element_located((By.ID, "widget_password")))
    password.send_keys(os.environ['PASSWORD'])

    login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[@id='nextButton_label']")))
    login_button.click()

    book_test_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@class='general-btn' and contains(@href, 'tbsloginredirect')]")))
    book_test_button.click()

    car_radio_button = wait.until(EC.element_to_be_clickable((By.ID, "CAR")))
    driver.execute_script("arguments[0].click();", car_radio_button)

    dt_radio_button = wait.until(EC.element_to_be_clickable((By.ID, "c1tt3")))
    driver.execute_script("arguments[0].click();", dt_radio_button)

    next_button = wait.until(EC.element_to_be_clickable((By.ID, "nextButton")))
    next_button.click()

    terms_checkbox = wait.until(EC.element_to_be_clickable((By.ID, "checkTerms")))
    terms_checkbox.click()

    next_button = wait.until(EC.element_to_be_clickable((By.ID, "nextButton")))
    next_button.click()

    location_radio_button = driver.find_element(By.ID, "rms_batLocLocSel")
    if not location_radio_button.is_selected():
        location_radio_button.click()

    all_locations_data = {}

    def extract_available_times():
        try:
            week_starting = driver.find_element(By.XPATH, "//span[@class='title']").text
            print(f"Week starting: {week_starting}")

            days = driver.find_elements(By.XPATH, "//span[@class='d']")
            day_dates = [day.text for day in days]

            times_by_day = {day: [] for day in day_dates}

            for day_index, day in enumerate(day_dates):
                available_times = driver.find_elements(By.XPATH, f"//td[contains(@class, 'rms_{day[:3].lower()}')]//a[contains(@class, 'available')]")
                for time_slot in available_times:
                    times_by_day[day].append(time_slot.text)

            for day, times in times_by_day.items():
                if times:
                    location_data[day] = times
                    print(f"{day}: {', '.join(times)}")
        except Exception as e:
            print(f"Error extracting times: {e}")

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
                location_dropdown = wait.until(EC.presence_of_element_located((By.ID, "rms_batLocationSelect2")))
                select = Select(location_dropdown)
                select.select_by_visible_text(location_name)

                print(f"Selected Location: {location_name}")

                next_button = wait.until(EC.element_to_be_clickable((By.ID, "nextButton")))
                next_button.click()

                time.sleep(1.5)

                no_timeslot_weeks = 0
                location_data = {}

                while True:
                    extract_available_times()

                    try:
                        alert_dialog = driver.find_element(By.XPATH, "//div[@role='alertdialog']")
                        alert_text = alert_dialog.text
                        if "There are no timeslots available for this week." in alert_text or "There are no timeslots available at this location." in alert_text:
                            no_timeslot_weeks += 1
                            print(f"No timeslots for week starting. Consecutive weeks with no slots: {no_timeslot_weeks}")
                            if no_timeslot_weeks >= 1:
                                print("Stopping search for this location after two consecutive weeks with no slots.")
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
                    print("Failed to navigate back to location selection. Exiting.")
                    break

            except Exception as e:
                print(f"An error occurred while processing location '{location_name}': {e}")
                continue

        break

    for location, data in all_locations_data.items():
        print(f"Data for {location}:")
        for day, times in data.items():
            print(f"  {day}: {', '.join(times)}")

    with open('data.json', 'w') as f:
        json.dump(all_locations_data, f, indent=4)
    print("Data has been saved to data.json")

finally:
    driver.quit()
