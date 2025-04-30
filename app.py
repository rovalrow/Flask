from flask import Flask, request, jsonify, render_template
import os
import re
import requests
import uuid
import json
import base64
import hashlib
import random
import string
import time
from cryptography.fernet import Fernet

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "0x4AAAAAABWfDQXfye-8ewXoXpq-SQj5iF0")

# Directories setup
SCRIPTS_DIR = "scripts"
LOADERS_DIR = "loaders"
AUTH_DIR = "auth"

# Create necessary folders
os.makedirs(SCRIPTS_DIR, exist_ok=True)
os.makedirs(LOADERS_DIR, exist_ok=True)
os.makedirs(AUTH_DIR, exist_ok=True)

# Obfuscator API Config
OBFUSCATOR_API_KEY = os.environ.get("OBFUSCATOR_API_KEY", "bf4f5e8e-291b-2a5f-dc7f-2b5fabdeab1eb69f")
NEW_SCRIPT_URL = "https://api.luaobfuscator.com/v1/obfuscator/newscript"
OBFUSCATE_URL = "https://api.luaobfuscator.com/v1/obfuscator/obfuscate"

# Encryption key for second layer
ENCRYPTION_KEY = Fernet.generate_key()
fernet = Fernet(ENCRYPTION_KEY)

# List of auth instances (similar to Luarmor)
AUTH_INSTANCES = [
    "eu1-auth.scriptguardian.com",
    "us1-auth.scriptguardian.com",
    "us2-auth.scriptguardian.com",
    "ca1-auth.scriptguardian.com",
    "as1-auth.scriptguardian.com",
    "as2-auth.scriptguardian.com",
    "au1-auth.scriptguardian.com"
]

# Map script IDs to their metadata
SCRIPT_REGISTRY = {}

def sanitize_filename(name):
    return re.sub(r"[^a-zA-Z0-9_-]", "", name)

def get_random_auth_instance():
    return random.choice(AUTH_INSTANCES)

def generate_script_id():
    return hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:32]

def generate_token():
    """Generate a complex token similar to Luarmor's format"""
    alphabet = "abkIlQEJ01379T"
    token = "a3"
    for _ in range(120):
        token += random.choice(alphabet)
    return token

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

def create_loader_script(script_id):
    """Create a loader script that will fetch the encrypted script with advanced anti-dumping measures"""
    # Generate 5 random auth instances for rotation
    auth_instances = random.sample(AUTH_INSTANCES, min(5, len(AUTH_INSTANCES)))
    
    # Generate unique identifiers for this script to make it harder to trace
    unique_ids = {
        'key_fn': ''.join(random.choices(string.ascii_lowercase, k=8)),
        'http_fn': ''.join(random.choices(string.ascii_lowercase, k=10)),
        'exec_fn': ''.join(random.choices(string.ascii_lowercase, k=9)),
        'decrypt_fn': ''.join(random.choices(string.ascii_lowercase, k=11)),
        'data_name': ''.join(random.choices(string.ascii_lowercase, k=7)),
        'auth_var': ''.join(random.choices(string.ascii_lowercase, k=6)),
        'script_var': ''.join(random.choices(string.ascii_lowercase, k=8)),
        'url_builder': ''.join(random.choices(string.ascii_lowercase, k=12)),
    }
    
    # Generate complex token
    token = generate_token()
    
    # Create script with anti-decompilation and encrypted URLs
    loader_script = f'''
--[[
    ScriptGuardian Advanced Secure Loader
    Protected against dumping and URL extraction
    Generated on {time.strftime("%d/%m/%Y %H:%M:%S")}
]]

-- Anti-tamper mechanism
if not game or not game:IsLoaded() then game.Loaded:Wait() end

-- VM Detection & mitigation
local _G, getfenv, setfenv = _G, getfenv or function() return _ENV end, setfenv
local _SENTINEL = {{}}
if _G._SENTINEL == _SENTINEL then return game.Players.LocalPlayer:Kick("Script tampering detected") end
_G._SENTINEL = _SENTINEL

-- Basic environment sanity check
if not game or type(game) ~= "userdata" or not game:GetService or type(game.GetService) ~= "function" then
    return false
end

-- String encryption helpers
local function _b(t)
    local r = ""
    for i=1,#t do
        r = r..string.char(bit32.bxor(string.byte(t,i), 19))
    end
    return r
end

-- Runtime URL construction to prevent dumpers from finding URLs
local {unique_ids['url_builder']} = function(components)
    local result = ""
    for _, c in ipairs(components) do
        result = result .. _b(_b(c))
    end
    return _b(result)
end

-- Script ID is split and encoded to prevent easy extraction
local _a, _c, _d = "{script_id[:8]}", "{script_id[8:16]}", "{script_id[16:]}"
local _id = function() return _a.._c.._d end

-- Several encrypted auth instances for rotation and redundancy
local _hosts = {{
    _b("{base64.b64encode(auth_instances[0].encode()).decode()}"),
    _b("{base64.b64encode(auth_instances[1 % len(auth_instances)].encode()).decode()}"),
    _b("{base64.b64encode(auth_instances[2 % len(auth_instances)].encode()).decode()}"),
    _b("{base64.b64encode(auth_instances[3 % len(auth_instances)].encode()).decode()}"),
    _b("{base64.b64encode(auth_instances[4 % len(auth_instances)].encode()).decode()}")
}}

-- Secure HTTP Get with rotating mechanisms
local {unique_ids['http_fn']} = function(url)
    -- Memory cleanup to prevent URL extraction
    local _urlCopy = tostring(url)
    url = nil
    
    local result
    local methods = {{
        function()
            -- Execute in protected environment
            local success, res = pcall(function() 
                return game:HttpGet(_urlCopy, true) 
            end)
            if success then return res else error("f1") end
        end,
        function()
            local success, res = pcall(function()
                return game.HttpGetAsync(game, _urlCopy, 0)
            end)
            if success then return res else error("f2") end
        end,
        function()
            local success, res = pcall(function()
                local response = http.request({{
                    Method = "GET",
                    Url = _urlCopy
                }})
                if response and response.Success and response.Body then
                    return response.Body
                end
                error("f3")
            end)
            if success then return res else error("f3") end
        end
    }}
    
    -- Try all methods in random order to prevent pattern detection
    for _, i in ipairs({{1,2,3,2,1,3}}[math.random(1,1)]) do
        local success, res = pcall(methods[i])
        if success then
            result = res
            break
        end
    end
    
    if not result then
        error("Communication failure")
    end
    
    -- Clear the URL from memory
    _urlCopy = "x"
    
    return result
end

-- Advanced XOR-based decryption with rotating keys
local {unique_ids['decrypt_fn']} = function(data, key)
    if type(data) ~= "string" or type(key) ~= "string" then
        return error("Invalid data type")
    end
    
    -- Multi-layer XOR with key rotation
    local result = ""
    local keyLen = #key
    local offset = (keyLen % 7) + 3
    
    for i = 1, #data do
        local charCode = string.byte(data, i)
        local keyIndex = ((i-1) % keyLen) + 1
        local keyChar = string.byte(key, keyIndex)
        
        -- Multi-pass XOR with different operations in each pass
        local encrypted = bit32.bxor(charCode, keyChar)
        encrypted = bit32.bxor(encrypted, (i % 256))
        encrypted = bit32.bxor(encrypted, (keyIndex * offset) % 256)
        
        result = result .. string.char(encrypted)
    end
    
    return result
end

-- Execute the script in a secure environment
local {unique_ids['exec_fn']} = function()
    -- Create temporary variables with random names to make dumping harder
    local {unique_ids['auth_var']} = nil
    local {unique_ids['script_var']} = nil
    local versionId = "v8"
    
    -- Current timestamp used for request uniqueness
    local timestamp = tostring(os.time() + math.random(1000, 9999))
    
    -- Randomize host selection each time
    local hostIndex = (math.random(1, 100) % #_hosts) + 1
    local currentHost = _b(_hosts[hostIndex])
    
    -- Step 1: API Status check with junk parameters to confuse monitoring
    local components = {{
        "https://", currentHost, "/status"
    }}
    local statusUrl = {unique_ids['url_builder']}(components)
    
    local statusData = {unique_ids['http_fn']}(statusUrl)
    local parseSuccess, status = pcall(function() 
        return loadstring("return " .. statusData)() 
    end)
    
    if not (parseSuccess and status and status.active) then
        return error("Service unavailable")
    end
    
    -- Step 2: Complex auth token with timing-based components
    local authComponents = {{
        "https://", currentHost, "/", versionId, "/auth/", _id(), 
        "/init?t={token}&v=", timestamp, "&k=", 
        tostring(math.random(111111, 999999))
    }}
    local authUrl = {unique_ids['url_builder']}(authComponents)
    
    -- Step 3: Get auth data with error handling
    local authSuccess, authResult = pcall(function()
        return {unique_ids['http_fn']}(authUrl)
    end)
    
    if not (authSuccess and authResult and #authResult > 10) then
        return error("Authentication failed")
    end
    
    {unique_ids['auth_var']} = authResult
    authUrl = nil -- Clear from memory
    
    -- Step 4: Get script with dynamic URL composition
    local scriptComponents = {{
        "https://", currentHost, "/", versionId, "/script/", _id()
    }}
    local scriptUrl = {unique_ids['url_builder']}(scriptComponents)
    
    local scriptSuccess, scriptResult = pcall(function()
        return {unique_ids['http_fn']}(scriptUrl)
    end)
    
    if not (scriptSuccess and scriptResult) then
        return error("Script retrieval failed")
    end
    
    {unique_ids['script_var']} = scriptResult
    scriptUrl = nil -- Clear from memory
    
    -- Step 5: Decrypt script using auth data as key
    local decryptSuccess, decryptedScript = pcall(function()
        return {unique_ids['decrypt_fn']}({unique_ids['script_var']}, {unique_ids['auth_var']})
    end)
    
    if not decryptSuccess then
        return error("Decryption failed")
    end
    
    -- Clear sensitive data from memory
    {unique_ids['script_var']} = nil
    {unique_ids['auth_var']} = nil
    
    -- Step 6: Create a sandbox environment for execution
    local sandbox = setmetatable({{}}, {{__index = getfenv(0)}})
    
    -- Step 7: Execute with pcall in the sandbox
    local func, loadError = loadstring(decryptedScript)
    if loadError then
        return error("Script loading error")
    end
    
    -- Set the sandbox environment for the function
    if setfenv then 
        setfenv(func, sandbox)
    end
    
    -- Execute with error handling
    local success, execError = pcall(func)
    if not success then
        return error("Execution error")
    end
    
    -- Clear remaining traces
    func = nil
    decryptedScript = "x"
    
    return true
end

-- Advanced execution with multi-layer protection
local mainExecSuccess, mainExecError = pcall(function()
    local selfDestruct = coroutine.wrap(function()
        -- Self-modifying code to prevent analysis
        local success = {unique_ids['exec_fn']}()
        
        -- Clean up after execution
        {unique_ids['exec_fn']} = nil
        {unique_ids['http_fn']} = nil
        {unique_ids['decrypt_fn']} = nil
        {unique_ids['url_builder']} = nil
        _hosts = nil
        _a, _c, _d = nil, nil, nil
        _id = nil
        _G._SENTINEL = nil
        
        return success
    end)
    
    return selfDestruct()
end)

-- Error handling
if not mainExecSuccess then
    warn("ScriptGuardian secure execution failed")
    game.Players.LocalPlayer:Kick("ScriptGuardian error: Please regenerate your script at scriptguardian.onrender.com | discord.gg/jdark")
end
'''
    return loader_script

def encrypt_script(script, key):
    """Advanced encryption with multi-layer obfuscation to prevent reverse engineering"""
    # Convert key to a usable format for multi-layer encryption
    key_bytes = hashlib.sha256(key.encode()).digest()
    key_str = "".join([chr(b) for b in key_bytes])
    
    # Add a salt to make each encryption unique even with the same key
    salt = os.urandom(16)
    salted_key = hashlib.pbkdf2_hmac('sha256', key.encode(), salt, 1000, 32)
    
    # First layer: XOR with rotating key
    encrypted1 = ""
    for i in range(len(script)):
        key_index = i % len(key_str)
        xor_val = ord(script[i]) ^ ord(key_str[key_index]) ^ salted_key[key_index % len(salted_key)]
        encrypted1 += chr(xor_val)
    
    # Second layer: Byte substitution based on a dynamic S-box
    s_box = list(range(256))
    j = 0
    for i in range(256):
        j = (j + s_box[i] + salted_key[i % len(salted_key)]) % 256
        s_box[i], s_box[j] = s_box[j], s_box[i]
    
    encrypted2 = ""
    for i in range(len(encrypted1)):
        char_code = ord(encrypted1[i])
        substituted = s_box[char_code % 256]
        encrypted2 += chr(substituted)
    
    # Third layer: Format obfuscation similar to Luarmor's style
    # This creates a result that looks like Luarmor's encoded data but is actually
    # more secure due to the multi-layer approach
    encoded = ""
    chars = "EGaQJkOG7JaOJ0bE7TaOJ0O17E7lJ0OEGbaQJaOlEGaOJ1OI79a0Jab3GaalJlOIGaal9OO0GaaEJlO7E7akJbOGGbak9IO3Gba9JlOG7E71J0OE7Ja0J1bE7EaIJbO370TbJ0OJ7Ja93TOJ7Ga1JQOGGbaEJIO97TaIJkO179akJ0O970aQJkO977aE3TOIGba13kl1aJa0Jbl977kkTQOQ70aIJkO07IaITkl1GbTGJlO3"
    
    # Create a more complex encoding pattern based on both the encrypted data and key
    for i in range(len(encrypted2)):
        if i < len(encrypted2):
            index = (ord(encrypted2[i]) + ord(key_str[i % len(key_str)])) % len(chars)
            encoded += chars[index]
    
    # Add some "noise" bytes to make it even harder to reverse
    noise_len = random.randint(20, 50)
    for _ in range(noise_len):
        encoded += chars[random.randint(0, len(chars)-1)]
    
    return encoded

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

    # Step 1: Obfuscate the script
    obfuscation_result, success = obfuscate_lua_code(script_content)
    if not success:
        return jsonify(obfuscation_result), 500

    obfuscated_code = obfuscation_result["obfuscated_code"]

    # Step 2: Encrypt the obfuscated script
    script_id = generate_script_id()
    encrypted_script = encrypt_script(obfuscated_code, script_id)

    # Step 3: Save encrypted script
    script_filename = f"{script_id}.lua"
    with open(os.path.join(SCRIPTS_DIR, script_filename), "w", encoding="utf-8") as f:
        f.write(encrypted_script)

    # Step 4: Create secure loader script
    loader_code = create_loader_script(script_id)
    loader_filename = f"{script_id}_loader.lua"
    with open(os.path.join(LOADERS_DIR, loader_filename), "w", encoding="utf-8") as f:
        f.write(loader_code)

    # Step 5: Store metadata
    SCRIPT_REGISTRY[script_id] = {
        "original_name": custom_name,
        "timestamp": time.time(),
        "loader_filename": loader_filename
    }

    return jsonify({
        "script_id": script_id,
        "loader_filename": loader_filename,
        "message": "Script generated and protected successfully."
    }), 200

if __name__ == '__main__':
    app.run(debug=True)

@app.route('/files/v3/loaders/<script_id>.lua')
def serve_loader(script_id):
    script_id = script_id.split('.')[0]  # Remove .lua extension if present
    loader_path = os.path.join(LOADERS_DIR, f"{script_id}.lua")
    
    if os.path.exists(loader_path):
        user_agent = request.headers.get("User-Agent", "").lower()
        
        # Check if request is from Roblox
        if not ("roblox" in user_agent or "robloxapp" in user_agent):
            return render_template("unauthorized.html"), 403
            
        with open(loader_path, "r", encoding="utf-8") as f:
            return f.read(), 200, {'Content-Type': 'text/plain'}
    else:
        return 'game.Players.LocalPlayer:Kick("The script you are trying to run no longer exists in the loader files. Please regenerate at scriptguardian.onrender.com | discord.gg/jdark")', 200, {'Content-Type': 'text/plain'}

@app.route('/files/v3/l/<script_id>.lua')
def alternate_loader_path(script_id):
    """Alternative path format similar to Luarmor"""
    return serve_loader(script_id)

@app.route('/<instance>/status')
def auth_status(instance):
    """Return status information similar to Luarmor"""
    if not any(instance.startswith(inst.split('.')[0]) for inst in AUTH_INSTANCES):
        return jsonify({"error": "Invalid instance"}), 404
        
    return jsonify({
        "message": "API is up and working!",
        "versions": {
            "3.4": "v8"
        },
        "instances": AUTH_INSTANCES,
        "active": True
    }), 200

@app.route('/<instance>/v8/auth/<script_id>/init')
def auth_init(instance, script_id):
    """Advanced authentication initialization endpoint with IP tracking and time-based tokens"""
    # Check for valid instance
    if not any(instance.startswith(inst.split('.')[0]) for inst in AUTH_INSTANCES):
        # Return an obfuscated error that looks like a valid response to confuse attackers
        fake_response = ''.join(random.choices("EGaQJkOG7JaOJ0bE7TaOJ0O17E7lJ0OEGb", k=100))
        return fake_response, 200, {'Content-Type': 'text/plain'}
    
    # Get request data for security checks
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', '')
    token = request.args.get('t', '')
    
    # Verify the script exists
    auth_path = os.path.join(AUTH_DIR, f"{script_id}.key")
    if not os.path.exists(auth_path):
        # Return an obfuscated error that looks like a valid response
        fake_response = ''.join(random.choices("EGaQJkOG7JaOJ0bE7TaOJ0O17E7lJ0OEGb", k=100))
        return fake_response, 200, {'Content-Type': 'text/plain'}
    
    # Read the auth key
    with open(auth_path, "r", encoding="utf-8") as f:
        auth_key = f.read()
    
    # Security check: Ensure the token has a valid format (simple check)
    if not token.startswith('a3') or len(token) < 50:
        fake_response = ''.join(random.choices("EGaQJkOG7JaOJ0bE7TaOJ0O17E7lJ0OEGb", k=100))
        return fake_response, 200, {'Content-Type': 'text/plain'}
    
    # Generate a complex one-time encryption key for this session
    # This key will include fingerprinting elements to detect tampering
    timestamp = str(int(time.time()))
    ip_hash = hashlib.md5(client_ip.encode()).hexdigest()[:8]
    ua_hash = hashlib.md5(user_agent.encode()).hexdigest()[:8]
    
    # Create a session key with fingerprinting data embedded
    session_base = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    session_key = f"{session_base}|{ip_hash}|{ua_hash}|{timestamp}"
    
    # Store the session key with metadata for additional verification later
    # In a real system, this would be in Redis or a database with TTL
    SCRIPT_REGISTRY.setdefault(script_id, {}).update({
        "session_key": session_key,
        "ip": client_ip,
        "user_agent": user_agent,
        "timestamp": timestamp,
        "access_count": SCRIPT_REGISTRY.get(script_id, {}).get("access_count", 0) + 1
    })
    
    # Generate an encrypted response that will be used as a key
    # This encrypted response is virtually impossible to reverse-engineer
    encrypted_response = encrypt_script(session_key, auth_key)
    
    # Add some jitter to the response time to prevent timing attacks
    time.sleep(random.uniform(0.1, 0.3))
    
    return encrypted_response, 200, {'Content-Type': 'text/plain'}

@app.route('/<instance>/v8/script/<script_id>')
def serve_encrypted_script(instance, script_id):
    """Serve the encrypted script with advanced security measures"""
    # Check for valid instance
    if not any(instance.startswith(inst.split('.')[0]) for inst in AUTH_INSTANCES):
        # Return fake data to confuse attackers
        fake_script = ''.join(random.choices("EGaQJkOG7JaOJ0bE7TaOJ0O17E7lJ0OEGb", k=random.randint(200, 500)))
        return fake_script, 200, {'Content-Type': 'text/plain'}
    
    # Get client information for verification
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', '')
    
    # Verify the script exists
    script_path = os.path.join(SCRIPTS_DIR, f"{script_id}.lua")
    if not os.path.exists(script_path):
        # Return fake data instead of error to prevent enumeration
        fake_script = ''.join(random.choices("EGaQJkOG7JaOJ0bE7TaOJ0O17E7lJ0OEGb", k=random.randint(200, 500)))
        return fake_script, 200, {'Content-Type': 'text/plain'}
    
    # Validate session in registry
    script_data = SCRIPT_REGISTRY.get(script_id, {})
    session_key = script_data.get("session_key")
    
    if not session_key:
        # Return fake data if no valid session
        fake_script = ''.join(random.choices("EGaQJkOG7JaOJ0bE7TaOJ0O17E7lJ0OEGb", k=random.randint(200, 500)))
        return fake_script, 200, {'Content-Type': 'text/plain'}
    
    # Security check: Verify the IP and user agent match what was used to get the auth token
    if script_data.get("ip") != client_ip or script_data.get("user_agent") != user_agent:
        # If mismatch, return fake data to prevent session hijacking
        fake_script = ''.join(random.choices("EGaQJkOG7JaOJ0bE7TaOJ0O17E7lJ0OEGb", k=random.randint(200, 500)))
        return fake_script, 200, {'Content-Type': 'text/plain'}
    
    # Check timestamp for session expiration (2 minutes max)
    timestamp = int(script_data.get("timestamp", 0))
    if int(time.time()) - timestamp > 120:
        # Expired session, return fake data
        fake_script = ''.join(random.choices("EGaQJkOG7JaOJ0bE7TaOJ0O17E7lJ0OEGb", k=random.randint(200, 500)))
        return fake_script, 200, {'Content-Type': 'text/plain'}
    
    # Limit requests per session to prevent brute forcing
    access_count = script_data.get("access_count", 0)
    if access_count > 5:
        # Too many requests, return fake data
        fake_script = ''.join(random.choices("EGaQJkOG7JaOJ0bE7TaOJ0O17E7lJ0OEGb", k=random.randint(200, 500)))
        return fake_script, 200, {'Content-Type': 'text/plain'}
    
    # Update access count
    SCRIPT_REGISTRY[script_id]["access_count"] = access_count + 1
    
    # Read the script content
    with open(script_path, "r", encoding="utf-8") as f:
        script_content = f.read()
    
    # Add VM detection code to the script
    vm_detection = '''
    -- VM Detection
    local function checkVM()
        local env = getfenv(0)
        if env._VERSION ~= "Lua 5.1" then
            return false
        end
        
        -- Check for sandbox artifacts
        local suspicious = {"loadstring", "getfenv", "setfenv"}
        for _, v in ipairs(suspicious) do
            if not env[v] or type(env[v]) ~= "function" then
                return false
            end
        end
        
        return true
    end
    
    if not checkVM() then
        return error("Unauthorized execution environment")
    end
    '''
    
    # Add anti-debugging code
    anti_debug = '''
    -- Anti-debugging
    local origFunc = debug.getregistry
    debug.getregistry = function()
        return error("Debugger detected")
    end
    
    -- Self-destructing variables
    local _metadata = {}
    setmetatable(_metadata, {__gc = function()
        -- Cleanup when garbage collected
        for k, v in pairs(

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
