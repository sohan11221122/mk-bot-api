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
    # 🟢 Render-এর জন্য Headless এবং অন্যান্য সেটিং
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # 🟢 Render সার্ভারের নিজস্ব Chromium ব্রাউজারের লোকেশন
    chrome_options.binary_location = "/usr/bin/chromium" 
    service = Service("/usr/bin/chromedriver")
    
    return webdriver.Chrome(service=service, options=chrome_options)

def run_mk_bot():
    print("🚀 Smart Cloud Bot Started for Render...")
    
    try:
        driver = setup_browser()
        wait = WebDriverWait(driver, 15)
        
        print("[*] Logging in to MK Network...")
        driver.get("http://mknetworkbd.com/auth.php")
        time.sleep(4)
        
        # লগইন বাইপাস (JS Injection)
        driver.execute_script("""
            var e = document.getElementsByName('phone_email')[0];
            if(e) e.value = 'sohan.shahel.sifa@gmail.com';
            var p = document.getElementsByName('password')[0];
            if(p) p.value = 'Sohan123@@##';
        """)
        time.sleep(1)
        
        try:
            driver.execute_script("document.getElementById('t-btnlog').click();")
        except:
            driver.find_element(By.ID, "t-btnlog").click()
            
        time.sleep(5)
        print("[+] Login Successful! Going to Get Number Page...")
        
        driver.get("http://mknetworkbd.com/getnum.php")
        time.sleep(5)

        while True:
            try:
                # 🟢 ১. সিগন্যাল চেক 
                try:
                    sig_res = requests.get(f"{API_BRIDGE_URL}?action=check_signal", timeout=10).json()
                    
                    if sig_res.get("signal") == "GET":
                        print("\n=============================================")
                        print("[*] 🔔 SIGNAL RECEIVED! Clicking GET NUMBER...")
                        print("=============================================\n")
                        
                        # সিগন্যাল রিসেট করা
                        requests.get(f"{API_BRIDGE_URL}?action=signal_received", timeout=5)
                        
                        target_range = requests.get(f"{API_BRIDGE_URL}?action=get_range", timeout=5).json().get('range', '')
                        if target_range:
                            driver.execute_script(f"document.querySelector('input[placeholder*=\"XXXXX\"]').value='{target_range}';")
                        
                        # ক্লিক করার আগে পুরনো ১ নম্বর লাইন সেভ করে রাখা
                        old_top = ""
                        rows = driver.find_elements(By.XPATH, "//table/tbody/tr")
                        if rows: old_top = rows[0].text
                        
                        # GET NUMBER ক্লিক
                        get_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'GET NUMBER')]")
                        driver.execute_script("arguments[0].click();", get_btn)
                        
                        # Smart Wait
                        print("[*] Waiting for table to update with fresh number...")
                        for _ in range(15):
                            time.sleep(1)
                            curr_rows = driver.find_elements(By.XPATH, "//table/tbody/tr")
                            if curr_rows and curr_rows[0].text != old_top:
                                break
                        
                        time.sleep(1) 
                        
                        # শুধুমাত্র নতুন আপডেট হওয়া প্রথম রো (Row) থেকে নাম্বার নেওয়া
                        rows = driver.find_elements(By.XPATH, "//table/tbody/tr")
                        if rows:
                            cols = rows[0].find_elements(By.TAG_NAME, "td")
                            if len(cols) >= 3: 
                                try: phone = cols[0].find_element(By.TAG_NAME, "span").text.strip()
                                except: phone = cols[0].text.strip()
                                phone = re.sub(r'[^0-9]', '', phone) 
                                
                                if phone:
                                    print(f"\n[+] 🎉 FRESH NUMBER EXTRACTED: {phone}")
                                    payload = {"phone": phone, "status": "PENDING", "otp": "Waiting..."}
                                    post_res = requests.post(f"{API_BRIDGE_URL}?action=save_number", json=payload, timeout=5)
                                    print(f"[*] DB Response: {post_res.text}\n")
                except Exception as check_e:
                    print(f"[-] Signal Check Error: {check_e}")

                # 🟢 ২. প্রথম ২৫ লাইন স্ক্যান করে রানিং নাম্বারের OTP আপডেট করা
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
                            requests.post(f"{API_BRIDGE_URL}?action=save_bulk_numbers", json={"numbers": bulk_data}, timeout=10)
                        except: pass

            except Exception as inner_e:
                print(f"[-] Main Loop Error: {inner_e}")
            
            time.sleep(3) 

    except Exception as e:
        print(f"❌ Critical Bot Error: {e}")
    finally:
        try:
            driver.quit()
        except:
            pass

@app.route('/')
def home():
    return jsonify({"status": "Cloud Bot is Running successfully on Render!"})

if __name__ == '__main__':
    threading.Thread(target=run_mk_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
