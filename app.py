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
import re
import os

app = Flask(__name__)
API_BRIDGE_URL = "http://sohan1020.onlinewebshop.net/api/api_bridge.php"

def setup_browser():
    chrome_options = Options()
    # Render Essential Settings
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Path for Render
    chrome_options.binary_location = "/usr/bin/chromium"
    service = Service("/usr/bin/chromedriver")
    
    return webdriver.Chrome(service=service, options=chrome_options)

def run_mk_bot():
    print("🚀 Bot Started...")
    while True:
        driver = None
        try:
            driver = setup_browser()
            print("[*] Logging in...")
            driver.get("http://mknetworkbd.com/auth.php")
            time.sleep(4)
            
            driver.execute_script("""
                var e = document.querySelector("input[placeholder='Enter phone or email']");
                if(e) e.value = 'sohan.shahel.sifa@gmail.com';
                var p = document.querySelector("input[placeholder='Enter password']");
                if(p) p.value = 'Sohan123@@##';
            """)
            time.sleep(1)
            
            try:
                driver.execute_script("document.getElementById('t-btnlog').click();")
            except:
                driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]").click()
            time.sleep(5)
            
            if "auth.php" in driver.current_url:
                print("❌ Login Failed.")
                driver.quit()
                time.sleep(30)
                continue
                
            print("[+] Login OK. Going to Get Number...")
            driver.get("http://mknetworkbd.com/getnum.php")
            time.sleep(5)

            while True:
                try:
                    # Signal Check
                    try:
                        sig_res = requests.get(f"{API_BRIDGE_URL}?action=check_signal", timeout=10).json()
                        if sig_res.get("signal") == "GET":
                            print("\n🔔 SIGNAL RECEIVED!")
                            requests.get(f"{API_BRIDGE_URL}?action=signal_received", timeout=5)
                            
                            target_range = requests.get(f"{API_BRIDGE_URL}?action=get_range", timeout=5).json().get('range', '')
                            if target_range:
                                driver.execute_script(f"document.querySelector('input[placeholder*=\"XXXXX\"]').value='{target_range}';")

                            old_rows = driver.find_elements(By.XPATH, "//table/tbody/tr")
                            old_top_text = old_rows[0].text if old_rows else ""

                            try:
                                driver.execute_script("document.getElementById('getBtn').click();")
                            except:
                                driver.find_element(By.XPATH, "//button[contains(text(), 'GET NUMBER')]").click()
                            
                            print("[*] Waiting for table update...")
                            for _ in range(15):
                                time.sleep(1)
                                curr_rows = driver.find_elements(By.XPATH, "//table/tbody/tr")
                                if curr_rows and curr_rows[0].text != old_top_text:
                                    break
                            
                            rows = driver.find_elements(By.XPATH, "//table/tbody/tr")
                            if rows:
                                cols = rows[0].find_elements(By.TAG_NAME, "td")
                                if len(cols) >= 1: 
                                    raw_text = cols[0].text
                                    phone = re.sub(r'[^0-9]', '', raw_text.split('\n')[0])
                                    if phone:
                                        print(f"✅ Number Saved: {phone}")
                                        payload = {"phone": phone, "status": "PENDING", "otp": "Waiting..."}
                                        requests.post(f"{API_BRIDGE_URL}?action=save_number", json=payload, timeout=5)
                    except Exception as check_e:
                        print(f"[-] Signal Error: {check_e}")

                    # Bulk Update
                    rows = driver.find_elements(By.XPATH, "//table/tbody/tr")
                    if rows:
                        bulk_data = []
                        for row in rows[:25]:
                            cols = row.find_elements(By.TAG_NAME, "td")
                            if len(cols) >= 2: 
                                raw_text = cols[0].text
                                phone = re.sub(r'[^0-9]', '', raw_text.split('\n')[0])
                                status_text = cols[1].text.strip()
                                otp = "N/A"
                                match = re.search(r'\b\d{4,6}\b', status_text) 
                                if match: otp = match.group(0)
                                
                                net_status = "PENDING"
                                if "SUCCESS" in status_text.upper() or otp != "N/A": net_status = "SUCCESS"
                                elif "CANCELED" in status_text.upper() or "EXPIRED" in status_text.upper(): net_status = "FAILED"
                                
                                if phone:
                                    bulk_data.append({"phone": phone, "otp": otp, "status": net_status})
                        if bulk_data:
                            requests.post(f"{API_BRIDGE_URL}?action=save_bulk_numbers", json={"numbers": bulk_data}, timeout=10)
                except Exception as inner_e:
                    print(f"[-] Inner Loop Error: {inner_e}")
                    if "session" in str(inner_e).lower():
                        break
                time.sleep(3)
        except Exception as e:
            print(f"❌ Critical Error: {e}")
            if driver: driver.quit()
            time.sleep(10)

@app.route('/')
def home():
    return jsonify({"status": "Running"})

if __name__ == '__main__':
    threading.Thread(target=run_mk_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
