from flask import Flask, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import requests
import threading
import re
import os

app = Flask(__name__)
API_BRIDGE_URL = "http://sohan1020.onlinewebshop.net/api/api_bridge.php"

def setup_browser():
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def run_mk_bot():
    print("🚀 Cloud Bot Started...")
    driver = setup_browser()
    wait = WebDriverWait(driver, 15)
    
    try:
        print("[*] Logging in to MK Network...")
        driver.get("http://mknetworkbd.com/auth.php")
        time.sleep(4)
        
        # 🟢 ১০০% ফিক্সড লগইন সিস্টেম (JavaScript Injection)
        email = "sohan.shahel.sifa@gmail.com"
        password = "Sohan123@@##"
        
        driver.execute_script(f"""
            var e = document.getElementsByName('phone_email')[0];
            if(e) e.value = '{email}';
            var p = document.getElementsByName('password')[0];
            if(p) p.value = '{password}';
        """)
        time.sleep(1)
        
        try:
            driver.execute_script("document.getElementById('t-btnlog').click();")
        except:
            print("[-] Button click failed via JS, trying normal click...")
            driver.find_element(By.ID, "t-btnlog").click()
            
        time.sleep(5)
        print("[+] Login Successful!")
        
        driver.get("http://mknetworkbd.com/getnum.php")
        time.sleep(5)

        while True:
            try:
                # ১. সিগন্যাল চেক এবং নতুন নাম্বার নেওয়া
                try:
                    sig_res = requests.get(f"{API_BRIDGE_URL}?action=check_signal", timeout=5).json()
                    if sig_res.get("signal") == "GET":
                        print("[*] 🔔 PC Bot requested a new number! Clicking GET NUMBER...")
                        requests.get(f"{API_BRIDGE_URL}?action=signal_received", timeout=5)
                        
                        target_range = requests.get(f"{API_BRIDGE_URL}?action=get_range", timeout=5).json().get('range', '')
                        if target_range:
                            driver.execute_script(f"document.querySelector('input[placeholder*=\"XXXXX\"]').value='{target_range}';")
                        
                        # GET NUMBER ক্লিক
                        get_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'GET NUMBER')]")
                        driver.execute_script("arguments[0].click();", get_btn)
                        time.sleep(8) 
                        
                        # শুধুমাত্র প্রথম রো (Row) থেকে নাম্বার নেওয়া
                        rows = driver.find_elements(By.XPATH, "//table/tbody/tr")
                        if rows:
                            cols = rows[0].find_elements(By.TAG_NAME, "td")
                            if len(cols) >= 3: 
                                try: phone = cols[0].find_element(By.TAG_NAME, "span").text.strip()
                                except: phone = cols[0].text.strip()
                                phone = re.sub(r'[^0-9]', '', phone) 
                                
                                if phone:
                                    print(f"[+] Fresh Number Sent to DB: {phone}")
                                    payload = {"phone": phone, "status": "PENDING", "otp": "Waiting..."}
                                    requests.post(f"{API_BRIDGE_URL}?action=save_number", json=payload, timeout=5)
                except: pass

                # ২. সবসময় প্রথম ২৫ লাইন স্ক্যান করে শুধুমাত্র রানিং নাম্বারের OTP আপডেট করা
                rows = driver.find_elements(By.XPATH, "//table/tbody/tr")
                if rows:
                    bulk_data = []
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
                            
                            net_status = "PENDING"
                            if "SUCCESS" in status_text.upper() or otp != "N/A": net_status = "SUCCESS"
                            elif "CANCELED" in status_text.upper() or "EXPIRED" in status_text.upper(): net_status = "FAILED"
                            
                            if phone:
                                bulk_data.append({"phone": phone, "otp": otp, "status": net_status})
                    
                    if bulk_data:
                        try:
                            # ডাটাবেস শুধু এক্সিস্টিং নাম্বারের OTP আপডেট করবে
                            requests.post(f"{API_BRIDGE_URL}?action=save_bulk_numbers", json={"numbers": bulk_data}, timeout=10)
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
    return jsonify({"status": "Cloud Bot is Running!"})

if __name__ == '__main__':
    threading.Thread(target=run_mk_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=10000)
