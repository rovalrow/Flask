from flask import Flask, request, jsonify, render_template, send_file
import os
import re
import requests
import uuid
import json

app = Flask(__name__, template_folder="templates")  # Make sure template folder is specified
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
        session_response.raise_for_status()  # <-- safer error handling
        session_data = session_response.json()

        if not session_data.get("sessionId"):
            return {"error": f"Failed to create session: {session_data.get('message', 'Unknown error')}"}, False

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
        obfuscate_response.raise_for_status()  # <-- safer error handling
        obfuscate_data = obfuscate_response.json()

        if not obfuscate_data.get("code"):
            return {"error": f"Failed to obfuscate: {obfuscate_data.get('message', 'Unknown error')}"}, False

        return {"obfuscated_code": obfuscate_data["code"]}, True

    except requests.RequestException as e:
        return {"error": f"Obfuscator service request error: {str(e)}"}, False
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}, False

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json(force=True)
    script_content = data.get("script", "").strip()
    custom_name = sanitize_filename(data.get("name", "").strip())

    if not script_content:
        return jsonify({"error": "No script provided"}), 400

    obfuscation_result, success = obfuscate_lua_code(script_content)

    if not success:
        return jsonify(obfuscation_result), 500

    obfuscated_script = obfuscation_result["obfuscated_code"]

    script_name = custom_name if custom_name else str(get_next_script_id())
    script_path = os.path.join(SCRIPTS_DIR, f"{script_name}.lua")

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(obfuscated_script)

    link = f"{request.url_root.rstrip('/')}/scriptguardian.shinzou/{script_name}"
    return jsonify({"link": link}), 200

@app.route('/scriptguardian.shinzou/<script_name>')
def execute(script_name):
    safe_name = sanitize_filename(script_name)
    script_path = os.path.join(SCRIPTS_DIR, f"{safe_name}.lua")

    if os.path.exists(script_path):
        user_agent = request.headers.get("User-Agent", "").lower()
        accept_header = request.headers.get("Accept", "").lower()

        if "text/html" in accept_header:
            return render_template("unauthorized.html")

        if "python" in user_agent or "curl" in user_agent:
            return render_template("cloudflare.html")

        # Serve the Lua file
        return send_file(script_path, mimetype="text/plain")

    return "Invalid script link.", 404

@app.route('/api/obfuscate', methods=['POST'])
def api_obfuscate():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    script_content = request.json.get("script", "").strip()
    if not script_content:
        return jsonify({"error": "No script provided"}), 400

    obfuscation_result, success = obfuscate_lua_code(script_content)
    if not success:
        return jsonify(obfuscation_result), 500

    return jsonify({"obfuscated_code": obfuscation_result["obfuscated_code"]}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host="0.0.0.0", port=port)
