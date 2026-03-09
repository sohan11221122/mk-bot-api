from flask import Flask, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time
import requests
import threading

app = Flask(__name__)

# আপনার AwardSpace API লিংক
API_BRIDGE_URL = "http://sohan1020.onlinewebshop.net/api/api_bridge.php"

def setup_browser():
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.binary_location = "/usr/bin/chromium" # Use Chromium
    
    service = Service("/usr/bin/chromedriver") # Use local driver
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def run_mk_bot():
    print("Bot Started...")
    driver = setup_browser()
    
    try:
        # Login to MK Network
        driver.get("http://mknetworkbd.com/auth.php")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//input[@type='email' or contains(@placeholder, 'email')]"))).send_keys("sohan.shahel.sifa@gmail.com")
        driver.find_element(By.XPATH, "//input[@type='password' or contains(@placeholder, 'password')]").send_keys("Sohan123@@##")
        driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]").click()
        
        time.sleep(3) 
        print("Logged in successfully!")

        # Go to Get Number page
        driver.get("http://mknetworkbd.com/getnum.php")
        time.sleep(3)

        while True:
            # Fetch Range from your AwardSpace panel
            res = requests.get(f"{API_BRIDGE_URL}?action=get_range")
            target_range = res.json().get('range', '')

            if not target_range:
                print("No range set in admin panel. Waiting...")
                time.sleep(10)
                continue

            print(f"Target Range: {target_range}")

            # Enter Range
            range_input = driver.find_element(By.XPATH, "//input[contains(@placeholder, 'XXXXX') or @type='text']")
            range_input.clear()
            range_input.send_keys(target_range)

            # Click Get Number
            driver.find_element(By.XPATH, "//button[contains(text(), 'GET NUMBER')]").click()
            time.sleep(5) 

            # Read Table Data
            try:
                phone = driver.find_element(By.XPATH, "//table//tbody/tr[1]/td[1]//span[1]").text
                status_text = driver.find_element(By.XPATH, "//table//tbody/tr[1]/td[2]").text 
                
                print(f"Got Number: {phone} | Status: {status_text}")

                # Send to your API
                payload = {
                    "phone": phone,
                    "status": "PENDING" if "SMS" in status_text else "SUCCESS",
                    "otp": status_text
                }
                requests.post(f"{API_BRIDGE_URL}?action=save_number", json=payload)
                
            except Exception as e:
                print("Could not find new number row. Retrying...")
            
            time.sleep(15) # Wait before next request

    except Exception as e:
        print(f"Bot Error: {e}")
    finally:
        driver.quit()

@app.route('/')
def home():
    return jsonify({"status": "MK Network Bot is Running!"})

if __name__ == '__main__':
    threading.Thread(target=run_mk_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=10000)
