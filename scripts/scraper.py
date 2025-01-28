from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select  # Import Select for dropdowns
import time
import collections
import json

def setup_driver(headless=False):
    """
    Set up the Selenium WebDriver with optional headless mode.
    """
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=chrome_options)  # Ensure ChromeDriver is in your PATH
    return driver

def login(driver, wait, license_number_str, password_str):
    """
    Perform login on the MyRTA portal.
    """
    # Open the login page
    driver.get("https://www.myrta.com/wps/portal/extvp/myrta/login/")

    # Wait for the license number field to be visible and enter the license number
    license_number = wait.until(EC.visibility_of_element_located((By.ID, "widget_cardNumber")))
    license_number.send_keys(license_number_str)

    # Wait for the password field to be visible and enter the password
    password = wait.until(EC.visibility_of_element_located((By.ID, "widget_password")))
    password.send_keys(password_str)
    
    # Locate and click the login button
    login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[@id='nextButton_label']")))
    login_button.click()

def navigate_to_booking(driver, wait):
    """
    Navigate to the booking page after logging in.
    """
    # Click the correct 'Book test' button using a more specific XPath
    book_test_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@class='general-btn' and contains(@href, 'tbsloginredirect')]")))
    book_test_button.click()

def select_test_type(driver, wait):
    """
    Select the test type (Car, DT) and proceed to the next step.
    """
    # Click on "Car" radio button
    car_radio_button = wait.until(EC.element_to_be_clickable((By.ID, "CAR")))
    driver.execute_script("arguments[0].click();", car_radio_button)

    # Wait for the options to load and click on "Driving Test (DT)" radio button
    dt_radio_button = wait.until(EC.element_to_be_clickable((By.ID, "c1tt3")))
    driver.execute_script("arguments[0].click();", dt_radio_button)

    # Click the "Next" button using the correct span ID
    next_button = wait.until(EC.element_to_be_clickable((By.ID, "nextButton")))
    next_button.click()

def agree_terms_and_proceed(driver, wait):
    """
    Agree to the eligibility terms and proceed to the next step.
    """
    # Check the eligibility terms checkbox
    terms_checkbox = wait.until(EC.element_to_be_clickable((By.ID, "checkTerms")))
    terms_checkbox.click()

    # Click the "Next" button again
    next_button = wait.until(EC.element_to_be_clickable((By.ID, "nextButton")))
    next_button.click()

def select_location(driver, wait):
    """
    Select the location radio button and reveal the location dropdown.
    """
    # Click the location radio button to reveal the dropdown if not already selected
    location_radio_button = driver.find_element(By.ID, "rms_batLocLocSel")
    if not location_radio_button.is_selected():
        location_radio_button.click()

    # Wait for the dropdown to load
    wait.until(EC.presence_of_element_located((By.ID, "rms_batLocationSelect2")))

def extract_available_times(driver, wait, location_data):
    """
    Extract available test times for the current week and store them in location_data.
    """
    try:
        # Wait for the week title to be visible and extract its text
        week_starting = wait.until(EC.visibility_of_element_located((By.XPATH, "//span[@class='title']"))).text
        print(f"\nWeek starting: {week_starting}")

        # Extract all day elements
        day_elements = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//span[@class='d']")))
        day_dates = [day.text.strip() for day in day_elements]

        # Initialize dictionary with default empty lists
        times_by_day = collections.defaultdict(list)

        # Extract all available time slots at once
        available_time_elements = driver.find_elements(By.XPATH, "//td[contains(@class, 'rms_')]/a[contains(@class, 'available')]")

        for time_slot in available_time_elements:
            try:
                # Extract the day class from the parent td element to map the time_slot to the correct day
                parent_td = time_slot.find_element(By.XPATH, "./ancestor::td")
                classes = parent_td.get_attribute("class").split()
                day_class = next((cls for cls in classes if cls.startswith("rms_")), None)
                if day_class:
                    day_abbr = day_class.replace("rms_", "").lower()  # e.g., 'rms_mon' -> 'mon'
                    day_full = {
                        'mon': 'Monday',
                        'tue': 'Tuesday',
                        'wed': 'Wednesday',
                        'thu': 'Thursday',
                        'fri': 'Friday',
                        'sat': 'Saturday',
                        'sun': 'Sunday'
                    }.get(day_abbr, day_abbr.capitalize())
                    times_by_day[day_full].append(time_slot.text.strip())
            except Exception as e:
                print(f"Error mapping time slot to day: {e}")
                continue

        # Store available test times by day, only if there are available times
        for day, times in times_by_day.items():
            if times:
                location_data[day] = times
                print(f"  {day}: {', '.join(times)}")  # Debug: Print times for each day

    except Exception as e:
        print(f"Error extracting times: {e}")

def main():
    
     LICENSE_NUMBER = os.getenv('LICENSE_NUMBER')
    PASSWORD = os.getenv('PASSWORD')

    if not LICENSE_NUMBER or not PASSWORD:
        raise ValueError("LICENSE_NUMBER and PASSWORD environment variables must be set")

    # Initialize WebDriver
    driver = setup_driver(headless=False)  # Set headless=True to run without a GUI

    try:
        # Set up WebDriverWait
        wait = WebDriverWait(driver, 15)  # Increased wait time for better stability

        # Perform login
        login(driver, wait, LICENSE_NUMBER, PASSWORD)

        # Navigate to booking page
        navigate_to_booking(driver, wait)

        # Select test type and proceed
        select_test_type(driver, wait)

        # Agree to terms and proceed
        agree_terms_and_proceed(driver, wait)

        # Select location and reveal dropdown
        select_location(driver, wait)

        # Locate the location dropdown and initialize Select object
        location_dropdown = wait.until(EC.presence_of_element_located((By.ID, "rms_batLocationSelect2")))
        select = Select(location_dropdown)
        location_options = select.options

        # Extract all location names, excluding the default "Choose..." option and any disabled options
        location_names = [
            option.text.strip() 
            for option in location_options 
            if option.text.strip().lower() != "choose..." and option.is_enabled()
        ]

        print(f"\nFound {len(location_names)} locations to process.")
        print("Locations:", ", ".join(location_names))  # Debug: Print all location names to verify

        # Dictionary to store data for all locations
        all_locations_data = {}

        # Iterate over each location
        for location_name in location_names:
            try:
                # Select the location by visible text
                select.select_by_visible_text(location_name)
                print(f"\nSelected Location: {location_name}")

                # Click the "Next" button to proceed
                wait.until(EC.element_to_be_clickable((By.ID, "nextButton"))).click()

                # Wait for the test times page to load by waiting for the week title to be visible
                wait.until(EC.presence_of_element_located((By.XPATH, "//span[@class='title']")))

                # Initialize a counter for consecutive alert dialogs
                no_timeslot_weeks = 0

                # Dictionary to store data for the current location
                location_data = {}

                # Loop through weeks and extract available times
                while True:
                    # Extract available times first
                    extract_available_times(driver, wait, location_data)

                    # Check for the alert dialog indicating no available times
                    try:
                        alert_dialog = driver.find_element(By.XPATH, "//div[@role='alertdialog']")
                        alert_text = alert_dialog.text
                        if ("There are no timeslots available for this week." in alert_text or
                            "There are no timeslots available at this location." in alert_text):
                            no_timeslot_weeks += 1
                            print(f"No timeslots for week starting. Consecutive weeks with no slots: {no_timeslot_weeks}")
                            if no_timeslot_weeks >= 2:
                                print("Stopping search for this location after two consecutive weeks with no slots.")
                                break
                    except:
                        # If the alert dialog is not found, reset the counter
                        no_timeslot_weeks = 0

                    # Check if the "Next week" button is available and click it
                    try:
                        next_week_button = wait.until(EC.element_to_be_clickable((By.ID, "nextWeekButton")))
                        next_week_button.click()
                        print("Navigated to next week.")
                        # Wait for the next week's data to load by waiting for the title to update
                        wait.until(EC.presence_of_element_located((By.XPATH, "//span[@class='title']")))
                    except:
                        print("No more weeks available or 'Next week' button not found.")
                        break

                # Store the data for the current location
                all_locations_data[location_name] = location_data

                # Navigate back to the location selection page using the provided link
                try:
                    back_to_locations_link = wait.until(EC.element_to_be_clickable((By.ID, "anotherLocationLink")))
                    back_to_locations_link.click()
                    print("Navigated back to location selection.")
                    # Wait until the location dropdown is present again
                    wait.until(EC.presence_of_element_located((By.ID, "rms_batLocationSelect2")))
                    # Re-initialize the Select object to avoid stale element reference
                    location_dropdown = wait.until(EC.presence_of_element_located((By.ID, "rms_batLocationSelect2")))
                    select = Select(location_dropdown)
                except:
                    print("Failed to navigate back to location selection. Exiting.")
                    break

            except Exception as e:
                print(f"An error occurred while processing location '{location_name}': {e}")
                continue  # Continue with the next location

        # Print the collected data
        print("\n=== Collected Available Test Times ===")
        for location, data in all_locations_data.items():
            print(f"\nLocation: {location}")
            if data:
                for day, times in data.items():
                    print(f"  {day}: {', '.join(times)}")
            else:
                print("  No available times.")

        # Optionally, save the data to a JSON file
        with open('available_test_times.json', 'w') as f:
            json.dump(all_locations_data, f, indent=4)
        print("\nAvailable test times have been saved to 'available_test_times.json'.")
        
        # Save to docs/data.json instead of the root directory
        with open('docs/data.json', 'w') as f:
            json.dump(all_locations_data, f, indent=4)
        print("\nAvailable test times have been saved to 'docs/data.json'.")

    finally:
        # Close the WebDriver
        driver.quit()
        print("\nWebDriver has been closed.")

if __name__ == "__main__":
    main()
