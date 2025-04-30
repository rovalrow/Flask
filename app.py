from flask import Flask, request, jsonify, render_template, Response
import os
import re
import requests
import uuid
import json

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "0x4AAAAAABWfDQXfye-8ewXoXpq-SQj5iF0")

SCRIPTS_DIR = "scripts"
os.makedirs(SCRIPTS_DIR, exist_ok=True)

OBFUSCATOR_API_KEY = os.environ.get("OBFUSCATOR_API_KEY", "bf4f5e8e-291b-2a5f-dc7f-2b5fabdeab1eb69f")
NEW_SCRIPT_URL = "https://api.luaobfuscator.com/v1/obfuscator/newscript"
OBFUSCATE_URL = "https://api.luaobfuscator.com/v1/obfuscator/obfuscate"

def sanitize_filename(name):
    return re.sub(r"[^a-zA-Z0-9_-]", "", name)

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

    if not script_content:
        return jsonify({"error": "No script provided"}), 400

    obfuscation_result, success = obfuscate_lua_code(script_content)

    if not success:
        return jsonify(obfuscation_result), 500

    obfuscated_script = obfuscation_result["obfuscated_code"]
    script_id = uuid.uuid4().hex[:32]
    script_path = os.path.join(SCRIPTS_DIR, f"{script_id}.lua")

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(obfuscated_script)

    return jsonify({"link": f"{request.host_url}l/{script_id}.lua"}), 200

@app.route('/l/<script_id>.lua')
def loader_script(script_id):
    script_id_clean = re.sub(r"[^a-zA-Z0-9]", "", script_id)
    internal_url = f"{request.host_url}_internal/{script_id_clean}.lua"
    loader_code = f'''
local HttpService = game:GetService("HttpService")
local response = http.request({{
    Url = "{internal_url}",
    Method = "GET"
}})
loadstring(response.Body)()
'''.strip()
    return Response(loader_code, mimetype='text/plain')

@app.route('/_internal/<script_id>.lua')
def internal_script(script_id):
    script_id_clean = re.sub(r"[^a-zA-Z0-9]", "", script_id)
    script_path = os.path.join(SCRIPTS_DIR, f"{script_id_clean}.lua")

    if not os.path.exists(script_path):
        return Response('-- Script not found', mimetype='text/plain')

    user_agent = request.headers.get("User-Agent", "").lower()

    if "roblox" not in user_agent and "robloxapp" not in user_agent:
        return render_template("unauthorized.html"), 403

    with open(script_path, "r", encoding="utf-8") as f:
        return Response(f.read(), mimetype='text/plain')

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
