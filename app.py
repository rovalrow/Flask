from flask import Flask, request, jsonify, render_template, Response
import os
import re
import requests
import uuid
import json
import base64
from supabase import create_client
import hashlib
import time

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "0x4AAAAAABZAawAfCPe3waqvkG4X_MxVenY")

# Supabase configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://ikxxvgflnpfyncnaqfxx.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlreHh2Z2ZsbnBmeW5jbmFxZnh4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDYxOTE3NTMsImV4cCI6MjA2MTc2Nzc1M30.YiF46ggItUYuKLfdD_6oOxq2xGX7ac6yqqtEGeM_dg8")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Obfuscator API Config
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

def encode_script_name(script_name):
    """Encode script name to make it harder to track in HTTP spy logs"""
    # Create a timestamp-based component to make each URL unique
    timestamp = str(int(time.time()))
    # Combine the script name with timestamp and a secret salt
    combined = f"{script_name}|{timestamp}|ScriptGuardian"
    # Generate a hash
    hashed = hashlib.sha256(combined.encode()).hexdigest()[:16]
    # Encode both the script name and timestamp with the hash
    encoded = base64.urlsafe_b64encode(f"{script_name}|{timestamp}|{hashed}".encode()).decode()
    return encoded

def decode_script_name(encoded_string):
    """Decode the script name from the encoded string"""
    try:
        # Decode the base64 string
        decoded = base64.urlsafe_b64decode(encoded_string.encode()).decode()
        # Split the components
        parts = decoded.split('|')
        if len(parts) != 3:
            return None
        
        script_name, timestamp, hash_value = parts
        # Verify the hash to ensure the URL wasn't tampered with
        expected_combined = f"{script_name}|{timestamp}|ScriptGuardian"
        expected_hash = hashlib.sha256(expected_combined.encode()).hexdigest()[:16]
        
        if hash_value == expected_hash:
            # Check if the URL is not too old (optional)
            current_time = int(time.time())
            url_time = int(timestamp)
            if current_time - url_time < 86400:  # 24 hours validity
                return script_name
        return None
    except Exception:
        return None

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
    
    # Generate script name
    script_name = custom_name if custom_name else uuid.uuid4().hex
    
    # Check if script name already exists in Supabase
    existing_scripts = supabase.table("scripts").select("name").eq("name", script_name).execute()
    
    # If script name exists, append a counter
    if existing_scripts.data:
        counter = 1
        while True:
            new_name = f"{script_name}{counter}"
            name_check = supabase.table("scripts").select("name").eq("name", new_name).execute()
            if not name_check.data:
                script_name = new_name
                break
            counter += 1

    # Store script in Supabase
    supabase.table("scripts").insert({
        "name": script_name,
        "content": obfuscated_script,
        "unobfuscated": script_content,
        "created_at": "now()"
    }).execute()

    # Encode the script name to make it harder to track in HTTP spy logs
    encoded_name = encode_script_name(script_name)
    
    # Anti-HTTP spy method 1: Return the URL in a modified format
    # This prevents the HttpSpy tool from correctly parsing and displaying the URL
    response_data = {
        "link_parts": {
            "host": request.host_url.rstrip('/'),
            "path": "scriptguardian/files/scripts/loaders",
            "id": encoded_name
        }
    }
    
    # Generate a client-side script to assemble the URL
    js_assembler = f"""
<script>
    // Anti-HTTP Spy URL assembly
    window.scriptUrl = '{response_data["link_parts"]["host"]}/' + 
                     '{response_data["link_parts"]["path"]}/' + 
                     '{response_data["link_parts"]["id"]}';
    document.getElementById('script_url').value = window.scriptUrl;
    document.getElementById('copy_button').onclick = function() {{
        navigator.clipboard.writeText(window.scriptUrl);
        alert('URL copied to clipboard!');
    }};
</script>
"""
    
    # Return a response with the URL parts that will be assembled client-side
    return jsonify(response_data), 200

@app.route('/scriptguardian/files/scripts/loaders/<encoded_script_name>')
def execute(encoded_script_name):
    # Decode the script name
    script_name = decode_script_name(encoded_script_name)
    if not script_name:
        return 'game.Players.LocalPlayer:Kick("Invalid or expired script URL. Please generate a new one.")', 200, {'Content-Type': 'text/plain'}
    
    # Sanitize for extra safety
    script_name = sanitize_filename(script_name)
    
    # Get script from Supabase
    response = supabase.table("scripts").select("content").eq("name", script_name).execute()
    
    if response.data:
        user_agent = request.headers.get("User-Agent", "").lower()

        # Check if request is NOT from Roblox
        if not ("roblox" in user_agent or "robloxapp" in user_agent):
            # Serve the Unauthorized HTML
            return render_template("unauthorized.html"), 403

        # Add headers that might confuse HTTP spy tools
        custom_headers = {
            'Content-Type': 'text/plain',
            'X-Anti-Spy': 'true',
            'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
            'Pragma': 'no-cache'
        }
        
        # Method 1: Deliver the script with custom response chunking
        # This can bypass some HTTP spy tools that expect a simple response
        script_content = response.data[0]["content"]
        
        # Method 2: Use a response stream to confuse HTTP spy tools
        def generate_script():
            # Add some junk data at the beginning that will be ignored by Roblox
            yield "--SCRIPT_GUARDIAN_BOUNDARY\n"
            # Yield the actual script in chunks
            chunk_size = 1024
            for i in range(0, len(script_content), chunk_size):
                yield script_content[i:i+chunk_size]
            # Add some junk data at the end that will be ignored by Roblox
            yield "\n--SCRIPT_GUARDIAN_END"
            
        return Response(generate_script(), headers=custom_headers)
    
    return 'game.Players.LocalPlayer:Kick("This Script is No Longer Existing on Our Database. Please Contact the Developer of the Script.")', 200, {'Content-Type': 'text/plain'}

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

@app.route('/instructions')
def instructions():
    """Serve a page that explains how to use the script properly"""
    return render_template("unauthorized.html")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
