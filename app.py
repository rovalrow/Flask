from flask import Flask, request, jsonify, render_template
import os
import re
import requests
import uuid
import json
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "0x4AAAAAABWfDQXfye-8ewXoXpq-SQj5iF0")  # Replace with a strong secret key

SCRIPTS_DIR = "scripts"
TOKENS = {}  # In-memory token storage (use a database for production)

# Create scripts folder if it doesn’t exist
os.makedirs(SCRIPTS_DIR, exist_ok=True)

# Obfuscator API Config
OBFUSCATOR_API_KEY = os.environ.get("OBFUSCATOR_API_KEY", "bf4f5e8e-291b-2a5f-dc7f-2b5fabdeab1eb69f")  # Replace with your API key
NEW_SCRIPT_URL = "https://api.luaobfuscator.com/v1/obfuscator/newscript"
OBFUSCATE_URL = "https://api.luaobfuscator.com/v1/obfuscator/obfuscate"

def sanitize_filename(name):
    return re.sub(r"[^a-zA-Z0-9_-]", "", name)

def obfuscate_lua_code(code):
    try:
        headers = {
            "apikey": OBFUSCATOR_API_KEY,
            "content-type": "text"
        }
        session_response = requests.post(NEW_SCRIPT_URL, headers=headers, data=code)
        session_data = session_response.json()
        if not session_data.get("sessionId"):
            return {"error": "Failed to create session"}, False

        session_id = session_data["sessionId"]

        obfuscate_headers = {
            "apikey": OBFUSCATOR_API_KEY,
            "sessionId": session_id,
            "content-type": "application/json"
        }

        obfuscation_options = {
            "MinifiyAll": True,
            "Virtualize": True,
            "Seed": str(uuid.uuid4().int)[:8],
            "CustomPlugins": {
                "CachedEncryptStrings": True,
                "CallRetAssignment": True,
                "ControlFlowFlattenV2AllBlocks": True,
                "DummyFunctionArgs": True,
                "FuncChopper": True,
                "Minifier2": True,
                "WowPacker": True
            }
        }

        obfuscate_response = requests.post(OBFUSCATE_URL, headers=obfuscate_headers, data=json.dumps(obfuscation_options))
        obfuscate_data = obfuscate_response.json()
        if not obfuscate_data.get("code"):
            return {"error": "Failed to obfuscate code"}, False

        return {"obfuscated_code": obfuscate_data["code"]}, True

    except Exception as e:
        return {"error": str(e)}, False

@app.route('/')
def home():
    return render_template("index.html")  # You’ll need an index.html for the frontend

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    script_content = data.get("script", "").strip()
    custom_name = sanitize_filename(data.get("name", "").strip())

    if not script_content:
        return jsonify({"error": "No script provided"}), 400

    obfuscation_result, success = obfuscate_lua_code(script_content)
    if not success:
        return jsonify(obfuscation_result), 500

    obfuscated_script = obfuscation_result["obfuscated_code"]
    base_name = custom_name if custom_name else uuid.uuid4().hex
    script_name = base_name
    counter = 1
    while os.path.exists(os.path.join(SCRIPTS_DIR, f"{script_name}.lua")):
        script_name = f"{base_name}{counter}"
        counter += 1

    script_path = os.path.join(SCRIPTS_DIR, f"{script_name}.lua")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(obfuscated_script)

    # Generate a unique token with a 1-hour expiration
    token = uuid.uuid4().hex
    expiration = datetime.now() + timedelta(hours=1)
    TOKENS[token] = {"script_name": script_name, "expiration": expiration}

    # Return a secure link with the token
    return jsonify({"link": f"{request.host_url}scriptguardian/files/scripts/loaders/{script_name}?token={token}"}), 200

@app.route('/scriptguardian/files/scripts/loaders/<script_name>')
def execute(script_name):
    script_path = os.path.join(SCRIPTS_DIR, f"{sanitize_filename(script_name)}.lua")

    if not os.path.exists(script_path):
        return 'game.Players.LocalPlayer:Kick("Script not found. Regenerate at scriptguardian.onrender.com")', 200, {'Content-Type': 'text/plain'}

    # Check for a valid token
    provided_token = request.args.get('token')
    if not provided_token or provided_token not in TOKENS:
        return render_template("unauthorized.html"), 403  # Create an unauthorized.html page

    # Validate token expiration and script match
    token_data = TOKENS[provided_token]
    if datetime.now() > token_data["expiration"]:
        del TOKENS[provided_token]  # Clean up expired token
        return render_template("unauthorized.html"), 403
    if token_data["script_name"] != script_name:
        return render_template("unauthorized.html"), 403

    # Serve the script if all checks pass
    with open(script_path, "r", encoding="utf-8") as f:
        return f.read(), 200, {'Content-Type': 'text/plain'}

@app.route('/api/obfuscate', methods=['POST'])
def api_obfuscate():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    script_content = request.json.get("script", "")
    if not script_content:
        return jsonify({"error": "No script provided"}), 400

    obfuscation_result, success = obfuscate_lua_code(script_content)
    if not success:
        return jsonify(obfuscation_result), 500

    return jsonify({"obfuscated_code": obfuscation_result["obfuscated_code"]}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
