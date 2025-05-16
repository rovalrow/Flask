from flask import Flask, request, jsonify, render_template
import os
import re
import requests
import uuid
import json
from supabase import create_client

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "0x4AAAAAABZAawAfCPe3waqvkG4X_MxVenY")

# Supabase configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://ikxxvgflnpfyncnaqfxx.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlreHh2Z2ZsbnBmeW5jbmFxZnh4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDYxOTE3NTMsImV4cCI6MjA2MTc2Nzc1M30.YiF46ggItUYuKLfdD_6oOxq2xGX7ac6yqqtEGeM_dg8")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Obfuscator config
OBFUSCATOR_API_KEY = os.environ.get("OBFUSCATOR_API_KEY", "bf4f5e8e-291b-2a5f-dc7f-2b5fabdeab1eb69f")
NEW_SCRIPT_URL = "https://api.luaobfuscator.com/v1/obfuscator/newscript"
OBFUSCATE_URL = "https://api.luaobfuscator.com/v1/obfuscator/obfuscate"

def sanitize_filename(name):
    return re.sub(r"[^a-zA-Z0-9_-]", "", name)

def obfuscate_lua_code(code):
    try:
        session_response = requests.post(NEW_SCRIPT_URL, headers={
            "apikey": OBFUSCATOR_API_KEY,
            "content-type": "text"
        }, data=code)

        session_id = session_response.json().get("sessionId")
        if not session_id:
            return {"error": "Failed to create session"}, False

        obfuscate_response = requests.post(OBFUSCATE_URL, headers={
            "apikey": OBFUSCATOR_API_KEY,
            "sessionId": session_id,
            "content-type": "application/json"
        }, data=json.dumps({
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
        }))

        code_result = obfuscate_response.json().get("code")
        if not code_result:
            return {"error": "Failed to obfuscate code"}, False

        return {"obfuscated_code": code_result}, True

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
    script_name = custom_name if custom_name else uuid.uuid4().hex

    existing = supabase.table("scripts").select("name").eq("name", script_name).execute()
    if existing.data:
        counter = 1
        while True:
            new_name = f"{script_name}{counter}"
            check = supabase.table("scripts").select("name").eq("name", new_name).execute()
            if not check.data:
                script_name = new_name
                break
            counter += 1

    supabase.table("scripts").insert({
        "name": script_name,
        "content": obfuscated_script,
        "unobfuscated": script_content,
        "created_at": "now()"
    }).execute()

    return jsonify({"link": f"{request.host_url}scriptguardian/files/scripts/loaders/{script_name}"}), 200

@app.route('/scriptguardian/files/scripts/loaders/<script_name>')
def execute(script_name):
    script_name = sanitize_filename(script_name)
    response = supabase.table("scripts").select("content").eq("name", script_name).execute()
    if response.data:
        ua = request.headers.get("User-Agent", "").lower()
        if not ("roblox" in ua or "robloxapp" in ua):
            return render_template("unauthorized.html"), 403
        return response.data[0]["content"], 200, {'Content-Type': 'text/plain'}

    return 'game.Players.LocalPlayer:Kick("Script no longer exists.")', 200, {'Content-Type': 'text/plain'}

@app.route('/scriptguardian/webhooks/create', methods=['POST'])
def create_webhook():
    data = request.get_json()
    raw_webhook = data.get("webhook", "")
    if not raw_webhook.startswith("https://discord.com/api/webhooks/"):
        return jsonify({"error": "Invalid webhook"}), 400

    webhook_id = uuid.uuid4().hex
    supabase.table("webhooks").insert({"id": webhook_id, "url": raw_webhook}).execute()
    return jsonify({"proxy": f"{request.host_url}scriptguardian/webhooks/send/{webhook_id}"})

@app.route('/scriptguardian/webhooks/send/<webhook_id>', methods=['POST'])
def send_webhook(webhook_id):
    result = supabase.table("webhooks").select("url").eq("id", webhook_id).execute()
    if not result.data:
        return jsonify({"error": "Webhook not found"}), 404

    real_webhook = result.data[0]['url']
    try:
        r = requests.post(real_webhook, json=request.json)
        return '', r.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
