# Imports
from database import connect, write_data, read_data, read_collection, delete_data, add_ttl
from flask import Flask, request, make_response, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import datetime, timedelta
import requests
import random
import string
import bcrypt
import os

# Analytics
import time
import psutil
import threading
process = psutil.Process()
ANALYTICS_URL = "https://discord.com/api/webhooks/1331972796351516702/Kgxr5biMp3Rzx0vAd0ck96rql6bKGbIS7LWAHFpQ876UTs2BoiR1mGFFf0fVKlKOocNr"
def analytics(message):
    try:
        payload = {'content': f"{message}"}
        response = requests.post(ANALYTICS_URL, json=payload)
        if response.status_code != 204:
            print(f"Failed to send webhook: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"Error sending to webhook: {e}", flush=True)

begin = datetime.now()
log_id = 0
def monitor_analytics():
    global log_id
    while True:
        cpu_percent = psutil.cpu_percent(interval=1)
        process_cpu_percent = process.cpu_percent(interval=1)

        memory_info = process.memory_info()
        rss = memory_info.rss / (1024 * 1024)
        vms = memory_info.vms / (1024 * 1024)
        system_memory_percent = psutil.virtual_memory().percent

        log_id += 1
        now = (datetime.now() - begin).total_seconds()
        
        report = f"**Analytics report #{log_id}, {int(now)}s:**\n"
        report += f"System CPU Usage: {cpu_percent}%\n"
        report += f"Process CPU Usage: {process_cpu_percent}%\n"
        report += f"Process Memory Usage (RSS): {rss:.2f} MB\n"
        report += f"Process Memory Usage (VMS): {vms:.2f} MB\n"
        report += f"System Memory Usage: {system_memory_percent}%\n"
        report += f"------------------------------------------"
        analytics(report)
        
        time.sleep(298)

analytics_thread = threading.Thread(target=monitor_analytics, daemon=True)
analytics_thread.start()

# Initialize apps
app = Flask(__name__)
limiter = Limiter(key_func=get_remote_address)
limiter.init_app(app)
CORS(app, supports_credentials=True)  # Add website domain later

# Define variables and functions
LOGGER_URL = 'https://discord.com/api/webhooks/1331662716796010657/MR-7PqEwmQptHo_mwQaeKQcszwCTrTBM79tQLACGKF4NdrET3AnFgx6VO5lnqV4LWMZr'
APPLICATION_URL = 'https://discord.com/api/webhooks/1331662932622446803/AFwCkoqGi2i-tEhIpL7WNegy6YXTMJKixJ3P8CbUuHwyyA3rJILEAchES27v3rYi6RRG'
cache = {}
cache["products"] = None
cache["products_lastsave"] = datetime.min

def webhook(message):
    try:
        payload = {'content': f"<@820933303616012288>: {message}"}
        response = requests.post(LOGGER_URL, json=payload)
        if response.status_code != 204:
            print(f"Failed to send webhook: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"Error sending to webhook: {e}", flush=True)


def random_string(length=100):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choices(characters, k=length))


def token(user, store):
    generated_token = random_string()
    write_data("accounts", "tokens", generated_token, add_ttl({"store": store, "account": user}))
    return generated_token


def verify_token(request):
    token = request.cookies.get("auth_token")
    if not token or not token.startswith('Bearer '):
        webhook("security triggered with false token")
        return False
    
    token = token.split(" ")[1]
    token_data = read_data("accounts", "tokens", token)
    if not token_data:
        return False

    told_data = request.get_json()
    user_from_request = request.headers.get('User')
    user_from_token = token_data.get('account')
    
    return user_from_request == user_from_token


def hash_password(password):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt)


def check_password(hashed_password, password):
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password)


def get_store_perms(name):
    stores = read_collection("accounts", "stores")
    for storename, storedata in stores.items():
        if storedata['owner'] == name:
            return {"storename": storename, "permissions": {"owner"}}
        if storedata['admins'].get(user):
            return {"storename": storename, "permissions": storedata['admins'][user]}
    return False


# Database initialization
try:
    connect("products_auth.json", "products")
    write_data("products", "products", "Test", {"name": "Good", "description": "Better", "price": 5.60})
except Exception as e:
    webhook(f"Products database initialization failed: {e}")

try:
    connect("accounts_auth.json", "accounts")
except Exception as e:
    webhook(f"Accounts database initialization failed: {e}")

webhook("Build done!")

# Define the API endpoints
@app.route('/admin', methods=['POST'])
@limiter.limit("3 per minute")
def admin():
    if not verify_token(request):
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    if not data or 'action' not in data:
        return jsonify({"error": "Missing required field: 'action'."}), 400

    document_action = data['action']
    collection_name = 'products'

    if document_action == "write":
        required_fields = ['key', 'data']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"error": f"Missing fields: {', '.join(missing_fields)}"}), 400

        document_key = data['key']
        document_data = data['data']
        real_data = {
            "description": document_data.get('description', "undefined"),
            "image": document_data.get('image', ""),
            "name": document_data.get('name', "undefined"),
            "price": document_data.get('price', 0),
        }

        try:
            write_data("products", collection_name, document_key, real_data)
            return jsonify({"success": True}), 200
        except Exception as e:
            return jsonify({"error": f"Failed to write data: {str(e)}"}), 500

    elif document_action == "delete":
        if 'key' not in data:
            return jsonify({"error": "Missing required field: 'key'."}), 400

        document_key = data['key']

        try:
            delete_data("products", collection_name, document_key)
            return jsonify({"success": True}), 200
        except Exception as e:
            return jsonify({"error": f"Failed to delete data: {str(e)}"}), 500

    return jsonify({"error": "Invalid action provided."}), 400


@app.route('/account', methods=['POST'])
#@limiter.limit("6 per minute")
def account():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    action = data.get('action')
    if action == "su":
        required_fields = ['user', 'pass']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"error": f"Missing fields: {', '.join(missing_fields)}"}), 400

        if read_data("accounts", "accounts", data['user']):
            return jsonify({"error": "Username is already taken"}), 409

        temp_data = {"pass": hash_password(data['pass']), "store": False}

        write_data("accounts", "accounts", data['user'], temp_data)
        temptoken = token(data['user'], False)
        response = make_response(jsonify({"success": True}))
        response.set_cookie(
            "auth_token",
            value=temptoken,
            httponly=True,
            secure=True,
            samesite="None",
            domain="lachene-server.onrender.com",
            max_age=7 * 24 * 60 * 60
        )
        return response, 201
    elif action == "li":
        required_fields = ['user', 'pass']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"error": f"Missing fields: {', '.join(missing_fields)}"}), 400

        account_data = read_data("accounts", "accounts", data['user'])
        if account_data and check_password(account_data['pass'], data['pass']):
            temptoken = token(data['user'], account_data['store'])
            response = make_response(jsonify({"success": True}))
            response.set_cookie(
                "auth_token",
                value=temptoken,
                httponly=True,
                secure=True,
                samesite="None",
                domain="lachene-server.onrender.com",
                max_age=7 * 24 * 60 * 60
            )
            return response, 201
        elif account_data:
            return jsonify({"error": "Invalid password"}), 401
        return jsonify({"error": "Account not found"}), 404

    return jsonify({"error": "Invalid action provided"}), 400


@app.route('/store', methods=['POST'])
@limiter.limit("5 per minute")
def store():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    action = data.get('action')
    if not user:
        return jsonify({"error": "No action provided"}), 400
    
    user = request.headers.get('User')
    if not user:
        return jsonify({"error": "No user provided"}), 400

    # Basic action
    if action == "get_store":
        stores = read_collection("accounts", "stores")
        store = get_store_perms(user)
        if store:
            return jsonify({"success": True, "storename": store["storename"]})
        else:
            return jsonify({"success": True, "storename": False})
    # Create store actions
    elif action == "create":
        if not verify_token(request):
            return jsonify({"error": "Unauthorized"}), 401

        data = data.get('data')
        if not data:
            return jsonify({"error": "No data content provided"}), 400

        message = "**New Shop Application**"
        message += f"\nAccount Name: {user}"
        message += f"\nLegal Name: {data.get('name', 'undefined')}"
        message += f"\nEmail: {data.get('email', 'undefined')}"
        message += f"\nPurpose: {data.get('purpose', 'undefined')}"
        message += "\n------------------------------------------"
        
        try:
            payload = {'content': f"<@820933303616012288> <@1295394121690775638>\n{message}"}
            response = requests.post(APPLICATION_URL, json=payload)
            if response.status_code != 204:
                print(f"Failed to send webhook: {response.status_code}, {response.text}")
                return jsonify({"error": "Application didn't send"}), 500
            else:
                return jsonify({"success": True}), 201
        except Exception as e:
            print(f"Error sending to webhook: {e}", flush=True)
            return jsonify({"error": "Application didn't send"}), 500
    elif action == "developer_create":
        if user not in ["Bjarnos", "Tunar"]:
            return jsonify({"error": "Unauthorized"}), 401
        
        if not verify_token(request):
            return jsonify({"error": "Unauthorized"}), 401

        data = data.get('data')
        if not data:
            return jsonify({"error": "No data content provided"}), 400

        shopname = data.get('name')
        owner = data.get('owner')
        if not shopname or not owner:
            return jsonify({"error": "Missing field 'name' or 'owner'."}), 400
        
        account_data = read_data("accounts", "accounts", owner)
        account_data["store"] = shopname
        write_data("accounts", "accounts", owner, account_data)
        write_data("accounts", "stores", shopname, {
            "owner": owner,
            "admins": {},
            "products": {},
            "codes": {}
        })
    # Store actions (for admin)
    elif action == "join":
        if not verify_token(request):
            return jsonify({"error": "Unauthorized"}), 401

        code = data.get('code')
        if not code:
            return jsonify({"error": "No code provided"}), 400

        stores = read_collection("accounts", "stores")
        for storename, storedata in stores.items():
            if code in storedata["codes"]:
                storedata["admins"][user] = {}
                write_data("accounts", "stores", storename, storedata)
                return jsonify({"success": True}), 201
        return jsonify({"error": "Invalid code"}), 400
    elif action == "change_admin":
        if not verify_token(request):
            return jsonify({"error": "Unauthorized"}), 401

        perms = get_store_perms(user)
        if not perms or not "admin" in perms["permissions"]:
            return jsonify({"error": "Not allowed"}), 403
        
        name = data.get('name')
        if not name:
            return jsonify({"error": "No name provided"}), 400

        account_data = read_data("accounts", "accounts", name)
        if not account_data:
            return jsonify({"error": "This user doesn't exist"}), 400

        if account_data["store"] != perms["storename"]:
            return jsonify({"error": "This user isn't a member of your store"}), 400

        permissions = data.get('perms')
        if not permissions:
            return jsonify({"error": "No permissions provided"}), 400

        pclone = []
        if "admin" in permissions:
            pclone.append("admin")
        else:
            if "create_products" in permissions:
                pclone.append("create_products")
            if "advertise" in permissions:
                pclone.append("advertise")
        
        old_data = read_data("accounts", "stores", name)
        old_data["admins"][name] = pclone
        write_data("accounts", "stores", name, old_data)
        return jsonify({"success": True}), 201
    elif action == "delete_admin":
        if not verify_token(request):
            return jsonify({"error": "Unauthorized"}), 401

        perms = get_store_data(user)
        if not perms or not "admin" in perms["permissions"]:
            return jsonify({"error": "Not allowed"}), 403
        
        name = data.get('name')
        if not name:
            return jsonify({"error": "No name provided"}), 400

        delete_data("accounts", "stores", name)
        return jsonify({"success": True}), 201

    return jsonify({"error": "Invalid action provided"}), 400


@app.route('/uploadimage', methods=['POST'])
@limiter.limit("3 per minute")
def uploadimage():
    data = request.form
    base64_image = data.get('image')
    if not data or not base64_image:
        return jsonify({"error": "Missing required fields 'image'."}), 400

    api_key = 'd3c92f2560b6cb4abdbb08e9a2395c75'
    payload = {
        'key': api_key,
        'image': base64_image
    }

    try:
        response = requests.post('https://api.imgbb.com/1/upload', data=payload)
        if response.status_code == 200:
            result = response.json()
            if result['success']:
                return jsonify({
                    'success': True,
                    'url': result['data']['url']
                })
            else:
                webhook(f"ImgBB API Error: {result.get('error', 'Unknown error')}")
                return jsonify({'success': False, 'error': result.get('error', 'Unknown error')}), 400
        else:
            webhook("ImgBB HTTP Error")
            return jsonify({'success': False, 'error': f"HTTP Error {response.status_code}"}), 400
    except Exception as e:
        webhook(f"Exception during ImgBB API call: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/get', methods=['GET'])
@limiter.limit("10 per minute")
def get():
    global cache
    global lastsave
    id = request.args.get('id')
    if not id:
        if not cache["products"] or datetime.now() - cache["products_lastsave"] > timedelta(minutes=1):
            cache["products_lastsave"] = datetime.now()
            cache["products"] = read_collection("products", "products")
        return jsonify({"success": True, "data": cache["products"]}), 200
    else:
        if not cache["products"] or datetime.now() - cache["products_lastsave"] > timedelta(minutes=1):
            cache["products_lastsave"] = datetime.now()
            cache["products"] = read_collection("products", "products")
        
        data = cache["products"].get(id)
        if data:
            return jsonify(data), 200
        else:
            return jsonify({"error": "Id not found"}), 404


@app.route('/ping', methods=['GET'])
@limiter.limit("1 per 9 minutes")
def ping():
    return jsonify({"response": "pong!"})


# Start the Flask server
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
