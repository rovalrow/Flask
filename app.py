from flask import Flask, request, jsonify, render_template
import os
import re
import requests
import uuid
import json

app = Flask(__name__)
SCRIPTS_DIR = "scripts"
os.makedirs(SCRIPTS_DIR, exist_ok=True)

OBFUSCATOR_API_KEY = os.environ.get("OBFUSCATOR_API_KEY", "your_api_key_here")
NEW_SCRIPT_URL = "https://api.luaobfuscator.com/v1/obfuscator/newscript"
OBFUSCATE_URL = "https://api.luaobfuscator.com/v1/obfuscator/obfuscate"
RECAPTCHA_SECRET = "6LdgdSgrAAAAAMAAFKzAKbUREwP9ShVuJfUk9SSe"
RECAPTCHA_SITEKEY = "6LdgdSgrAAAAAL7zsuu9Lh-cEeTFdmB0BbFu3Ntr"

def sanitize_filename(name):
    return re.sub(r"[^a-zA-Z0-9_-]", "", name)

def obfuscate_lua_code(code):
    try:
        session_response = requests.post(
            NEW_SCRIPT_URL,
            headers={"apikey": OBFUSCATOR_API_KEY, "content-type": "text"},
            data=code
        )
        session_data = session_response.json()
        if not session_data.get("sessionId"):
            return {"error": "Failed to create session"}, False

        obfuscate_response = requests.post(
            OBFUSCATE_URL,
            headers={
                "apikey": OBFUSCATOR_API_KEY,
                "sessionId": session_data["sessionId"],
                "content-type": "application/json"
            },
            data=json.dumps({
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
            })
        )
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
    base_name = custom_name or uuid.uuid4().hex
    script_name = base_name
    counter = 1
    while os.path.exists(os.path.join(SCRIPTS_DIR, f"{script_name}.lua")):
        script_name = f"{base_name}{counter}"
        counter += 1

    script_path = os.path.join(SCRIPTS_DIR, f"{script_name}.lua")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(obfuscated_script)

    return jsonify({"link": f"{request.host_url}scriptguardian/files/scripts/loaders/{script_name}"}), 200

@app.route('/scriptguardian/files/scripts/loaders/<script_name>', methods=['GET', 'POST'])
def execute(script_name):
    script_path = os.path.join(SCRIPTS_DIR, f"{sanitize_filename(script_name)}.lua")

    if not os.path.exists(script_path):
        return 'game.Players.LocalPlayer:Kick("This script no longer exists.")', 200, {'Content-Type': 'text/plain'}

    user_agent = request.headers.get("User-Agent", "").lower()
    is_roblox = "roblox" in user_agent or "robloxapp" in user_agent

    if is_roblox:
        with open(script_path, "r", encoding="utf-8") as f:
            return f.read(), 200, {'Content-Type': 'text/plain'}

    if request.method == 'POST':
        token = request.form.get('g-recaptcha-response', '')
        if not token:
            return jsonify({"error": "Missing CAPTCHA token"}), 400

        response = requests.post("https://www.google.com/recaptcha/api/siteverify", data={
            'secret': RECAPTCHA_SECRET,
            'response': token
        })

        result = response.json()
        if result.get("success"):
            with open(script_path, "r", encoding="utf-8") as f:
                return f.read(), 200, {'Content-Type': 'text/plain'}
        else:
            return "CAPTCHA verification failed", 403

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <title>Access Denied</title>
        <script src="https://www.google.com/recaptcha/api.js" async defer></script>
        <style>
            body {{
                font-family: Arial;
                background-color: #1a1e30;
                color: white;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }}
            .container {{
                text-align: center;
                padding: 30px;
            }}
            .discord-button {{
                margin-top: 20px;
                padding: 12px 24px;
                background-color: #000;
                color: white;
                border: none;
                border-radius: 10px;
                cursor: pointer;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>⛔ Access Denied</h1>
            <p>Complete the CAPTCHA to access this script.</p>
            <form method="POST">
                <div class="g-recaptcha" data-sitekey="{RECAPTCHA_SITEKEY}"></div>
                <br>
                <button type="submit" class="discord-button">I'm not a robot</button>
            </form>
        </div>
    </body>
    </html>
    """, 403

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
    app.run(host='0.0.0.0', port=port)
