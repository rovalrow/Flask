from flask import Flask, request, jsonify, render_template
import os
import re
import requests
import uuid
import json

app = Flask(__name__)
SCRIPTS_DIR = "scripts"

# Create scripts folder if it doesn't exist
os.makedirs(SCRIPTS_DIR, exist_ok=True)

# Obfuscator API Config
OBFUSCATOR_API_KEY = os.environ.get("OBFUSCATOR_API_KEY", "bf4f5e8e-291b-2a5f-dc7f-2b5fabdeab1eb69f")
NEW_SCRIPT_URL = "https://api.luaobfuscator.com/v1/obfuscator/newscript"
OBFUSCATE_URL = "https://api.luaobfuscator.com/v1/obfuscator/obfuscate"

def sanitize_filename(name):
    return re.sub(r"[^a-zA-Z0-9_-]", "", name)

def get_next_script_id():
    existing_files = [f.split(".")[0] for f in os.listdir(SCRIPTS_DIR) if f.endswith(".lua")]
    script_numbers = [int(f) for f in existing_files if f.isdigit()]
    return max(script_numbers, default=0) + 1

def obfuscate_lua_code(code):
    try:
        new_script_headers = {
            "apikey": OBFUSCATOR_API_KEY,
            "content-type": "text"
        }
        session_response = requests.post(NEW_SCRIPT_URL, headers=new_script_headers, data=code)
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
    return render_template("index.html")

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

    return jsonify({"link": f"{request.host_url}scriptguardian/files/scripts/loaders/{script_name}"}), 200

@app.route('/scriptguardian/files/scripts/loaders/<script_name>')
def execute(script_name):
    script_path = os.path.join(SCRIPTS_DIR, f"{sanitize_filename(script_name)}.lua")

    if os.path.exists(script_path):
        user_agent = request.headers.get("User-Agent", "").lower()

        # Check if request is NOT from Roblox
        if not ("roblox" in user_agent or "robloxapp" in user_agent):
            # Serve the Unauthorized HTML
            return """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta content="width=device-width,initial-scale=1" name="viewport">
                <title>Unauthorized</title>
                <style>
                    body {
                        margin: 0;
                        font-family: Roboto, Arial, sans-serif;
                        background-color: #1a1e30;
                        color: #fff;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        height: 100vh;
                    }
                    .container {
                        text-align: center;
                        padding: 20px;
                        background: rgba(255, 255, 255, 0);
                        border-radius: 10px;
                        box-shadow: 0 8px 15px transparent;
                    }
                    .brand {
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        margin-bottom: 20px;
                    }
                    .brand-text {
                        font-size: 18px;
                        font-weight: 600;
                        color: #fff;
                        margin-top: 5px;
                    }
                    h1 {
                        font-size: 24px;
                        margin-bottom: 10px;
                    }
                    p {
                        font-size: 16px;
                        color: #d1d1d1;
                    }
                    .discord-button { 
                        margin-top: 20px;
                        padding: 12px 24px; 
                        font-size: 20px; 
                        background-color: #000000; 
                        color: white; 
                        border: none; 
                        border-radius: 12px; 
                        cursor: pointer; 
                        font-family: 'Fredoka', sans-serif;
                        transition: 0.3s;
                    }
                    .discord-button:hover { 
                        background-color: #222222; 
                    }
                    .made-by {
                        margin-top: 15px;
                        color: red;
                        font-size: 18px;
                        font-family: 'Fredoka', sans-serif;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="brand">
                        <div class="brand-text">⛔ Access Denied ⛔</div>
                    </div>
                    <h1>You do not have permission to view these files.</h1>
                    <p>Please close this page and continue to a valid location.</p>
                    <button class="discord-button" onclick="window.location.href='https://discord.gg/xHXTSFXcUu'">Discord</button>
                    <div class="made-by">Made By: Shinzou</div>
                </div>
            </body>
            </html>
            """, 403

        # If User-Agent is Roblox, send raw Lua script
        with open(script_path, "r", encoding="utf-8") as f:
            return f.read(), 200, {'Content-Type': 'text/plain'}

        return 'game.Players.LocalPlayer:Kick("The script youre trying to run does no longer exists in the loader files, Please regenerate again at scriptguardian.onrender.com | discord.gg/jdark")', 200, {'Content-Type': 'text/plain'}      

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
    
