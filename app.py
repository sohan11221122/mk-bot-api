from flask import Flask, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time
import requests
import threading
import re
import os

app = Flask(__name__)

API_BRIDGE_URL = "http://sohan1020.onlinewebshop.net/api/api_bridge.php"

def setup_browser():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    chrome_options.binary_location = "/usr/bin/chromium" 
    service = Service("/usr/bin/chromedriver")

    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def run_mk_bot():
    print("🚀 Smart Bot Thread Started...")
    driver = setup_browser()
    
    try:
        print("[*] Logging in to MK Network...")
        driver.get("http://mknetworkbd.com/auth.php")
        time.sleep(5)
        
        email = "sohan.shahel.sifa@gmail.com"
        password = "Sohan123@@##"
        
        driver.execute_script(f"var e = document.querySelector(\"input[placeholder='Enter phone or email']\"); if(e) e.value = '{email}';")
        driver.execute_script(f"var p = document.querySelector(\"input[placeholder='Enter password']\"); if(p) p.value = '{password}';")
        
        try: driver.execute_script("document.getElementById('t-btnlog').click();")
        except: driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]").click()
            
        time.sleep(5)
        print("[+] Login Successful!")

        driver.get("http://mknetworkbd.com/getnum.php")
        time.sleep(3)

        while True:
            try:
                # ১. চেক করবে পিসি থেকে নতুন নাম্বারের রিকোয়েস্ট এসেছে কি না
                try:
                    sig_res = requests.get(f"{API_BRIDGE_URL}?action=check_signal", timeout=5).json()
                    if sig_res.get("signal") == "GET":
                        print("[*] 🔔 PC Bot requested a new number! Clicking GET NUMBER...")
                        requests.get(f"{API_BRIDGE_URL}?action=signal_received", timeout=5)
                        
                        res_range = requests.get(f"{API_BRIDGE_URL}?action=get_range", timeout=5)
                        target_range = res_range.json().get('range', '')
                        if target_range:
                            driver.execute_script(f"document.querySelector('input[placeholder*=\"XXXXX\"]').value='{target_range}';")
                        
                        driver.execute_script("document.getElementById('getBtn').click();")
                        print("[+] Clicked! Waiting 6s for table to update...")
                        time.sleep(6)
                except: pass

                # ২. সবসময় টেবিল চেক করবে (নাম্বার এবং ওটিপি আপডেট করার জন্য)
                rows = driver.find_elements(By.XPATH, "//table/tbody/tr")
                if rows:
                    first_row = rows[0]
                    cols = first_row.find_elements(By.TAG_NAME, "td")
                    
                    if len(cols) >= 3: 
                        try: phone = cols[0].find_element(By.TAG_NAME, "span").text.strip()
                        except: phone = cols[0].text.strip()
                        
                        phone = re.sub(r'[^0-9]', '', phone) 
                        status_text = cols[1].text.strip()
                        
                        otp = "N/A"
                        match = re.search(r'\b\d{4,6}\b', status_text) 
                        if match: otp = match.group(0)
                        
                        current_status = "PENDING"
                        if "SUCCESS" in status_text.upper() or otp != "N/A": current_status = "SUCCESS"
                        elif "CANCELED" in status_text.upper() or "EXPIRED" in status_text.upper(): current_status = "FAILED"
                        
                        if phone:
                            payload = {"phone": phone, "status": current_status, "otp": otp}
                            try: requests.post(f"{API_BRIDGE_URL}?action=save_number", json=payload, timeout=5)
                            except: pass

            except Exception as inner_e:
                pass
            
            time.sleep(5) 

    except Exception as e:
        print(f"❌ Critical Bot Error: {e}")
    finally:
        driver.quit()

@app.route('/')
def home():
    return jsonify({"status": "Smart MK Network Bot is Running!", "version": "6.0"})

if __name__ == '__main__':
    t = threading.Thread(target=run_mk_bot)
    t.daemon = True
    t.start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
