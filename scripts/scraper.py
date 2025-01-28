from seleniumwire import webdriver  # Changed this import
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
import time
import json
import os
import logging

# Add logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Selenium Wire options
seleniumwire_options = {
    'verify_ssl': False,
    'suppress_connection_errors': False
}

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.114 Safari/537.36")

# Initialize the driver with Selenium Wire
driver = webdriver.Chrome(
    options=chrome_options,
    seleniumwire_options=seleniumwire_options
)

# Add request interceptor
def interceptor(request):
    del request.headers['Referer']  # Delete the referer to help avoid detection
    request.headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    request.headers['Accept-Language'] = 'en-US,en;q=0.5'

driver.request_interceptor = interceptor

try:
    # Add debug log
    logger.info("Navigating to login page...")
    driver.get("https://www.myrta.com/wps/portal/extvp/myrta/login/")
    time.sleep(5)

    # Add page information logs
    logger.info("Page title: %s", driver.title)
    logger.info("Current URL: %s", driver.current_url)
    
    # Set up WebDriverWait
    wait = WebDriverWait(driver, 30)

    # Add debug log
    logger.info("Waiting for license number field...")
    license_number = wait.until(EC.visibility_of_element_located((By.ID, "widget_cardNumber")))
    logger.info("License number field found, entering credentials...")
    license_number.send_keys(os.getenv('LICENSE_NUMBER'))
    
    # Wait for the password field to be visible and enter the password
    password = wait.until(EC.visibility_of_element_located((By.ID, "widget_password")))
    password.send_keys(os.getenv('PASSWORD'))
    
    # Wait for the booking page to load
    time.sleep(1)

    # Locate and click the login button
    login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[@id='nextButton_label']")))
    login_button.click()


    # Click the correct 'Book test' button using a more specific XPath
    book_test_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@class='general-btn' and contains(@href, 'tbsloginredirect')]")))
    book_test_button.click()

    # Wait for the booking page to load
    time.sleep(1)
    
    # Click on "Car" radio button
    car_radio_button = wait.until(EC.element_to_be_clickable((By.ID, "CAR")))
    driver.execute_script("arguments[0].click();", car_radio_button)

    # Wait for the options to load and click on "Driving Test (DT)" radio button
    dt_radio_button = wait.until(EC.element_to_be_clickable((By.ID, "c1tt3")))
    driver.execute_script("arguments[0].click();", dt_radio_button)

   # Wait a little for changes to register
    time.sleep(1)

  # Click the "Next" button using the correct span ID
    next_button = wait.until(EC.element_to_be_clickable((By.ID, "nextButton")))
    next_button.click()

    # Wait for navigation to the next step
    time.sleep(1)
    
    # Check the eligibility terms checkbox
    terms_checkbox = wait.until(EC.element_to_be_clickable((By.ID, "checkTerms")))
    terms_checkbox.click()
    
    # Wait for navigation to the next step
    time.sleep(1)

    # Click the "Next" button again
    next_button = wait.until(EC.element_to_be_clickable((By.ID, "nextButton")))
    next_button.click()

    # Wait for navigation to the next step
    time.sleep(1)
    
   # Click the location radio button to reveal the dropdown if not already selected
    location_radio_button = driver.find_element(By.ID, "rms_batLocLocSel")
    if not location_radio_button.is_selected():
        location_radio_button.click()

    # Wait for the dropdown to load
    time.sleep(1)

    # Dictionary to store data for all locations
    all_locations_data = {}

    # Function to extract available test times for the current week
    def extract_available_times():
        try:
            week_starting = driver.find_element(By.XPATH, "//span[@class='title']").text
            print(f"Week starting: {week_starting}")

            # Extract dates for each day of the week
            days = driver.find_elements(By.XPATH, "//span[@class='d']")
            day_dates = [day.text for day in days]

            # Create a dictionary to hold available times for each day
            times_by_day = {day: [] for day in day_dates}

            # Extract available test times and map them to the correct day
            for day_index, day in enumerate(day_dates):
                available_times = driver.find_elements(By.XPATH, f"//td[contains(@class, 'rms_{day[:3].lower()}')]//a[contains(@class, 'available')]")
                for time_slot in available_times:
                    times_by_day[day].append(time_slot.text)

            # Store available test times by day, only if there are available times
            for day, times in times_by_day.items():
                if times:  # Only store days with available times
                    location_data[day] = times
                    print(f"{day}: {', '.join(times)}")  # Debug: Print times for each day
        except Exception as e:
            print(f"Error extracting times: {e}")

    # Iterate over each location
    while True:
        # Re-locate the dropdown and re-initialize the Select object
        location_dropdown = wait.until(EC.presence_of_element_located((By.ID, "rms_batLocationSelect2")))
        select = Select(location_dropdown)
        location_options = select.options

        # **Start of Changes**
        # Extract all location names, excluding the default "Choose..." option and any disabled options
        location_names = [
            option.text.strip() 
            for option in location_options 
            if option.text.strip().lower() != "choose..." and option.is_enabled()
        ]
        # **End of Changes**

        print(f"Found {len(location_names)} locations to process.")
        print("Locations:", ", ".join(location_names))  # Debug: Print all location names to verify

        for location_name in location_names:
            try:
                # **Start of Changes**
                # Re-locate the dropdown and select the location by visible text
                location_dropdown = wait.until(EC.presence_of_element_located((By.ID, "rms_batLocationSelect2")))
                select = Select(location_dropdown)
                select.select_by_visible_text(location_name)
                # **End of Changes**
                
                print(f"Selected Location: {location_name}")

                # Click the "Next" button to proceed
                next_button = wait.until(EC.element_to_be_clickable((By.ID, "nextButton")))
                next_button.click()

                # Wait for the test times page to load
                time.sleep(1.5)

                # Initialize a counter for consecutive alert dialogs
                no_timeslot_weeks = 0

                # Dictionary to store data for the current location
                location_data = {}

                # Loop through weeks and extract available times
                while True:
                    # Extract available times first
                    extract_available_times()

                    # Check for the alert dialog indicating no available times
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
                        # If the alert dialog is not found, reset the counter
                        no_timeslot_weeks = 0

                    # Check if the "Next week" button is available and click it
                    try:
                        next_week_button = wait.until(EC.element_to_be_clickable((By.ID, "nextWeekButton")))
                        next_week_button.click()
                        time.sleep(1)  # Wait for the next week's data to load
                    except:
                        print("No more weeks available or 'Next week' button not found.")
                        break

                # Store the data for the current location
                all_locations_data[location_name] = location_data

                # Navigate back to the location selection page using the provided link
                try:
                    back_to_locations_link = wait.until(EC.element_to_be_clickable((By.ID, "anotherLocationLink")))
                    back_to_locations_link.click()
                    time.sleep(2)
                except:
                    print("Failed to navigate back to location selection. Exiting.")
                    break

            except Exception as e:
                print(f"An error occurred while processing location '{location_name}': {e}")
                continue  # Continue with the next location

        # Break the outer loop if all locations have been processed
        break

    # Print or store the collected data
    for location, data in all_locations_data.items():
        print(f"Data for {location}:")
        for day, times in data.items():
            print(f"  {day}: {', '.join(times)}")
            
    os.makedirs('docs', exist_ok=True)
    with open('docs/data.json', 'w') as f:
        json.dump(all_locations_data, f, indent=4)
    print("Data has been saved to docs/data.json")


finally:
    # Close the WebDriver
    driver.quit()
