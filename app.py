# Imports
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import json
import requests

# Initialize Flask app
app = Flask(__name__)
limiter = Limiter(key_func=get_remote_address)
limiter.init_app(app)
CORS(app, resources={r"/*": {"origins": "https://bjarnos.github.io", "http://127.0.0.1:5500"}}) # remove selfhost later

def load_universe_ids():
    try:
        with open("gameids.json", "r") as file:
            data = json.load(file)
            return data.get("universe_ids", [])
    except FileNotFoundError:
        return []

def load_extra_descriptions():
    try:
        with open("extra_descriptions.json", "r") as file:
            data = json.load(file)
            return data.get("data", {})
    except FileNotFoundError:
        return {}

def fetch_game_data(universe_ids, extra_descriptions):
    api_url = "https://games.roblox.com/v1/games"
    response = requests.get(api_url, params={"universeIds": ",".join(map(str, universe_ids))})

    if response.status_code != 200:
        return {"error": "Failed to fetch data from Roblox API"}

    data = response.json().get("data", [])
    
    games = []
    for game in data:
        game_id = game.get("id")
        
        thumbnail_response = requests.get(
            "https://thumbnails.roblox.com/v1/games/icons",
            params={
                "universeIds": game_id,
                "size": "512x512",
                "format": "Png",
                "isCircular": "false"
            }
        )
        thumbnail_data = thumbnail_response.json().get("data", [])
        thumbnail_url = thumbnail_data[0].get("imageUrl", "Assets/thumbnail.png") if thumbnail_data else "Assets/thumbnail.png"

        description = extra_descriptions.get(str(game_id), ["No description available", "Unknown time"])

        games.append({
            "name": game.get("name"),
            "active_users": game.get("playing"),
            "total_plays": game.get("visits"),
            "root_place": game.get("rootPlaceId"),
            "thumbnail_url": thumbnail_url,
            "extra_description": description[0],
            "time_spent": description[1]
        })
    
    return games

# Define API endpoints
@app.route('/ping', methods=['GET'])
@limiter.limit("1 per 9 minutes")
def ping():
    return jsonify({"response": "pong!"})

@app.route('/get', methods=['GET'])
@limiter.limit("5 per minute")
def get_game_data():
    universe_ids = load_universe_ids()
    extra_descriptions = load_extra_descriptions()

    if not universe_ids:
        return jsonify({"error": "No universe IDs found"}), 400

    game_data = fetch_game_data(universe_ids, extra_descriptions)
    return jsonify({"data": game_data}), 200

# Start the Flask server
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
