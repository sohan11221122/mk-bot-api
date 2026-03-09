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
    return webdriver.Chrome(service=service, options=chrome_options)

def run_mk_bot():
    print("🚀 Smart Bot (Top 25) Started...")
    driver = setup_browser()
    
    try:
        driver.get("http://mknetworkbd.com/auth.php")
        time.sleep(5)
        
        driver.execute_script("var e=document.querySelector(\"input[placeholder='Enter phone or email']\"); if(e) e.value='sohan.shahel.sifa@gmail.com';")
        driver.execute_script("var p=document.querySelector(\"input[placeholder='Enter password']\"); if(p) p.value='Sohan123@@##';")
        
        try: driver.execute_script("document.getElementById('t-btnlog').click();")
        except: driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]").click()
            
        time.sleep(5)
        driver.get("http://mknetworkbd.com/getnum.php")
        time.sleep(3)

        while True:
            try:
                # সিগন্যাল চেক
                try:
                    sig_res = requests.get(f"{API_BRIDGE_URL}?action=check_signal", timeout=5).json()
                    if sig_res.get("signal") == "GET":
                        print("[*] 🔔 Signal Received! Clicking GET NUMBER...")
                        requests.get(f"{API_BRIDGE_URL}?action=signal_received", timeout=5)
                        
                        target_range = requests.get(f"{API_BRIDGE_URL}?action=get_range", timeout=5).json().get('range', '')
                        if target_range:
                            driver.execute_script(f"document.querySelector('input[placeholder*=\"XXXXX\"]').value='{target_range}';")
                        
                        driver.execute_script("document.getElementById('getBtn').click();")
                        time.sleep(6)
                except: pass

                # 🟢 NEW: প্রথম ২৫টি রো (Row) চেক করা এবং Bulk Update
                rows = driver.find_elements(By.XPATH, "//table/tbody/tr")
                if rows:
                    bulk_data = []
                    # প্রথম ২৫ টি রো লুপ করবে
                    for row in rows[:25]:
                        cols = row.find_elements(By.TAG_NAME, "td")
                        if len(cols) >= 3: 
                            try: phone = cols[0].find_element(By.TAG_NAME, "span").text.strip()
                            except: phone = cols[0].text.strip()
                            
                            phone = re.sub(r'[^0-9]', '', phone) 
                            status_text = cols[1].text.strip()
                            
                            otp = "N/A"
                            match = re.search(r'\b\d{4,6}\b', status_text) 
                            if match: otp = match.group(0)
                            
                            if phone:
                                bulk_data.append({"phone": phone, "otp": otp})
                    
                    # ডাটাবেসে একসাথে সব ডাটা পাঠানো
                    if bulk_data:
                        try:
                            requests.post(f"{API_BRIDGE_URL}?action=save_bulk_numbers", json={"numbers": bulk_data}, timeout=10)
                            print(f"[+] Bulk Scanned & Updated {len(bulk_data)} numbers in DB.")
                        except Exception as e:
                            print(f"[-] Bulk API Error: {e}")

            except Exception as inner_e:
                pass
            
            time.sleep(5) 

    except Exception as e:
        print(f"❌ Critical Bot Error: {e}")
    finally:
        driver.quit()

@app.route('/')
def home():
    return jsonify({"status": "Smart MK Network Bot (25 Rows) is Running!", "version": "7.0"})

if __name__ == '__main__':
    threading.Thread(target=run_mk_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
