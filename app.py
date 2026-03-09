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

# আপনার AwardSpace API লিংক
API_BRIDGE_URL = "http://sohan1020.onlinewebshop.net/api/api_bridge.php"

def setup_browser():
    chrome_options = Options()
    # Render বা সার্ভারের জন্য প্রয়োজনীয় আর্গুমেন্ট
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Render সাধারণত Chromium ব্যবহার করে
    # যদি লোকাল PC তে রান করেন তাহলে এই ২ লাইন কমেন্ট করে দিন
    chrome_options.binary_location = "/usr/bin/chromium" 
    service = Service("/usr/bin/chromedriver")
    
    # যদি লোকাল PC তে রান করান, তাহলে নিচের লাইনটি ব্যবহার করুন (কমেন্ট সরিয়ে)
    # from webdriver_manager.chrome import ChromeDriverManager
    # service = Service(ChromeDriverManager().install())

    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def run_mk_bot():
    print("🚀 Bot Thread Started...")
    driver = setup_browser()
    
    try:
        # ১. লগইন প্রসেস
        print("[*] Logging in to MK Network...")
        driver.get("http://mknetworkbd.com/auth.php")
        time.sleep(5)
        
        # JS দিয়ে ইনপুট ফিল করা (সবচেয়ে স্টেবল মেথড)
        email = "sohan.shahel.sifa@gmail.com"
        password = "Sohan123@@##"
        
        driver.execute_script(f"""
            var e = document.querySelector("input[placeholder='Enter phone or email']");
            if(e) e.value = '{email}';
        """)
        driver.execute_script(f"""
            var p = document.querySelector("input[placeholder='Enter password']");
            if(p) p.value = '{password}';
        """)
        
        # লগইন বাটন ক্লিক
        try:
            driver.execute_script("document.getElementById('t-btnlog').click();")
        except:
            # যদি ID না থাকে
            driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]").click()
            
        time.sleep(5)
        print("[+] Login Successful!")

        # ২. গেট নাম্বার পেজে যাওয়া
        driver.get("http://mknetworkbd.com/getnum.php")
        time.sleep(3)

        while True:
            try:
                # API থেকে রেঞ্জ আনা
                res = requests.get(f"{API_BRIDGE_URL}?action=get_range")
                target_range = res.json().get('range', '')

                if not target_range:
                    print("[-] No range set in admin panel. Waiting 10s...")
                    time.sleep(10)
                    continue

                # রেঞ্জ ইনপুট এবং বাটন ক্লিক
                print(f"[*] Setting Range: {target_range}")
                driver.execute_script(f"document.querySelector('input[placeholder*=\"XXXXX\"]').value='{target_range}';")
                
                # আইডি দিয়ে ক্লিক (আগের সমস্যা সমাধান)
                driver.execute_script("document.getElementById('getBtn').click();")
                print("[+] GET NUMBER Clicked! Waiting for response...")
                time.sleep(6) 

                # ৩. টেবিল থেকে ডাটা রিড করা (নতুন আপডেটেড লজিক)
                print("[*] Searching for numbers in the table...")
                time.sleep(5) # টেবিল লোড হওয়ার জন্য সময়
                
                # শুধু tbody এর ভেতরের tr গুলো খুঁজুন
                rows = driver.find_elements(By.XPATH, "//table/tbody/tr")
                
                if rows:
                    first_row = rows[0]
                    # পুরো Row-এর টেক্সট প্রিন্ট করুন ডিবাগিং এর জন্য
                    print(f"[DEBUG] Row Text: {first_row.text}")
                    
                    cols = first_row.find_elements(By.TAG_NAME, "td")
                    
                    # সাধারণত ফোন নাম্বার, স্ট্যাটাস এবং অ্যাকশন কলাম থাকে
                    if len(cols) >= 3: 
                        try:
                            phone = cols[0].find_element(By.TAG_NAME, "span").text.strip()
                        except:
                            phone = cols[0].text.strip()
                        
                        # নাম্বার থেকে স্পেস বা অন্য ক্যারেক্টার বাদ দেওয়া
                        phone = re.sub(r'[^0-9]', '', phone) 
                        
                        status_text = cols[1].text.strip()
                        
                        # OTP বের করার লজিক
                        otp = "N/A"
                        match = re.search(r'\b\d{4,6}\b', status_text) 
                        if match:
                             otp = match.group(0)
                        
                        # স্ট্যাটাস ঠিক করা
                        current_status = "PENDING"
                        if "SUCCESS" in status_text.upper() or otp != "N/A":
                            current_status = "SUCCESS"
                        elif "CANCELED" in status_text.upper() or "EXPIRED" in status_text.upper():
                            current_status = "FAILED"
                        
                        if phone:
                            print(f"📱 Number: {phone} | Status: {current_status} | OTP: {otp}")

                            # API তে ডাটা সেন্ড
                            payload = {
                                "phone": phone,
                                "status": current_status,
                                "otp": otp
                            }
                            try:
                                res = requests.post(f"{API_BRIDGE_URL}?action=save_number", json=payload)
                                print(f"[+] Data sent to API. Response: {res.text}")
                            except Exception as api_err:
                                print(f"[-] API Error: {api_err}")
                        else:
                            print("[-] Could not extract phone number from column.")
                    else:
                        print(f"[-] Table row does not have enough columns (found {len(cols)}).")
                else:
                    print("[-] No rows found in table yet.")

            except Exception as inner_e:
                print(f"[-] Loop Error: {inner_e}")
            
            # পরবর্তী চেকের জন্য অপেক্ষা (১০ সেকেন্ড পর পর চেক করবে)
            time.sleep(10) 

    except Exception as e:
        print(f"❌ Critical Bot Error: {e}")
    finally:
        driver.quit()

@app.route('/')
def home():
    return jsonify({"status": "MK Network Bot is Running!", "version": "5.4"})

if __name__ == '__main__':
    # ব্যাকগ্রাউন্ড থ্রেডে বট চালু করা
    t = threading.Thread(target=run_mk_bot)
    t.daemon = True
    t.start()
    
    # ফ্লাস্ক অ্যাপ রান করা (Render এ পোর্ট 10000 থাকে সাধারণত)
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
