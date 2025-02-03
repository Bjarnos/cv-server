# Imports
from flask import Flask, request, make_response, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address=
import os

# Initialize apps
app = Flask(__name__)
limiter = Limiter(key_func=get_remote_address)
limiter.init_app(app)
CORS(app)  # Add website domain later

# Define the API endpoints
@app.route('/ping', methods=['GET'])
@limiter.limit("1 per 9 minutes")
def ping():
    return jsonify({"response": "pong!"})

# Start the Flask server
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
