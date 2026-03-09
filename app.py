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
    # Render-এর জন্য প্রয়োজনীয় সেটিংস
    chrome_options.add_argument("--headless=new") # New headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Render সার্ভারে Chromium এর লোকেশন
    chrome_options.binary_location = "/usr/bin/chromium" 
    service = Service("/usr/bin/chromedriver")
    
    return webdriver.Chrome(service=service, options=chrome_options)

def run_mk_bot():
    print("🚀 Smart Cloud Bot Started for Render...")
    
    while True: # Main Loop to restart driver if it crashes
        driver = None
        try:
            driver = setup_browser()
            wait = WebDriverWait(driver, 15)
            
            print("[*] Logging in to MK Network...")
            driver.get("http://mknetworkbd.com/auth.php")
            time.sleep(4)
            
            # Login Bypass (Fixed: Using Placeholder)
            driver.execute_script("""
                var e = document.querySelector("input[placeholder='Enter phone or email']");
                if(e) e.value = 'sohan.shahel.sifa@gmail.com';
                var p = document.querySelector("input[placeholder='Enter password']");
                if(p) p.value = 'Sohan123@@##';
            """)
            time.sleep(1)
            
            # Login Click (Fixed: Trying ID first)
            try:
                driver.execute_script("document.getElementById('t-btnlog').click();")
            except:
                try:
                    driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]").click()
                except:
                    print("[-] Login button click failed, trying submit...")
                    driver.execute_script("document.forms[0].submit();")
                
            time.sleep(5)
            
            if "auth.php" in driver.current_url:
                print("❌ Login Failed! Check credentials.")
                driver.quit()
                time.sleep(60)
                continue
                
            print("[+] Login Successful! Going to Get Number Page...")
            
            driver.get("http://mknetworkbd.com/getnum.php")
            time.sleep(5)

            # Inner Loop for polling
            while True:
                try:
                    # ১. সিগন্যাল চেক
                    try:
                        sig_res = requests.get(f"{API_BRIDGE_URL}?action=check_signal", timeout=10).json()
                        
                        if sig_res.get("signal") == "GET":
                            print("\n=============================================")
                            print("[*] 🔔 SIGNAL RECEIVED! Clicking GET NUMBER...")
                            print("=============================================\n")
                            
                            # সিগন্যাল রিসেট
                            requests.get(f"{API_BRIDGE_URL}?action=signal_received", timeout=5)
                            
                            # রেঞ্জ সেট
                            target_range = requests.get(f"{API_BRIDGE_URL}?action=get_range", timeout=5).json().get('range', '')
                            if target_range:
                                driver.execute_script(f"document.querySelector('input[placeholder*=\"XXXXX\"]').value='{target_range}';")

                            # পুরনো রো সেভ
                            old_rows = driver.find_elements(By.XPATH, "//table/tbody/tr")
                            old_top_text = old_rows[0].text if old_rows else ""

                            # GET NUMBER ক্লিক (Fixed: ID 'getBtn')
                            try:
                                driver.execute_script("document.getElementById('getBtn').click();")
                            except:
                                driver.find_element(By.XPATH, "//button[contains(text(), 'GET NUMBER')]").click()
                            
                            print("[*] Waiting for table to update...")
                            for _ in range(15):
                                time.sleep(1)
                                curr_rows = driver.find_elements(By.XPATH, "//table/tbody/tr")
                                if curr_rows and curr_rows[0].text != old_top_text:
                                    break
                            
                            # নতুন নাম্বার এক্সট্রাক্ট
                            rows = driver.find_elements(By.XPATH, "//table/tbody/tr")
                            if rows:
                                cols = rows[0].find_elements(By.TAG_NAME, "td")
                                if len(cols) >= 1: 
                                    # নাম্বার প্রথম কলাম থেকে নেওয়া
                                    raw_text = cols[0].text
                                    phone = re.sub(r'[^0-9]', '', raw_text.split('\n')[0])
                                    
                                    if phone:
                                        print(f"\n[+] 🎉 FRESH NUMBER EXTRACTED: {phone}")
                                        payload = {"phone": phone, "status": "PENDING", "otp": "Waiting..."}
                                        post_res = requests.post(f"{API_BRIDGE_URL}?action=save_number", json=payload, timeout=5)
                                        print(f"[*] DB Response: {post_res.text}\n")
                    except Exception as check_e:
                        print(f"[-] Signal Check Error: {check_e}")

                    # ২. OTP আপডেট (Bulk Scan)
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
                            try:
                                requests.post(f"{API_BRIDGE_URL}?action=save_bulk_numbers", json={"numbers": bulk_data}, timeout=10)
                            except: pass

                except Exception as inner_e:
                    print(f"[-] Inner Loop Error: {inner_e}")
                    # যদি সেশন এক্সপায়ার হয় তাহলে ব্রেক করে আউটার লুপে গিয়ে রিলগইন করবে
                    if "no such window" in str(inner_e).lower() or "session deleted" in str(inner_e).lower():
                        break
                
                time.sleep(3)

        except Exception as e:
            print(f"❌ Critical Bot Error: {e}")
            if driver:
                try: driver.quit()
                except: pass
            print("[*] Restarting bot in 10 seconds...")
            time.sleep(10)

@app.route('/')
def home():
    return jsonify({"status": "Cloud Bot is Running successfully on Render!"})

if __name__ == '__main__':
    threading.Thread(target=run_mk_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
