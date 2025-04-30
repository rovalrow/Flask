from flask import Flask, request, jsonify, render_template, Response, redirect, url_for
import os
import re
import requests
import uuid
import json
import time
import hashlib
import hmac
from functools import wraps
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import secure_filename

app = Flask(__name__)
# Apply ProxyFix to handle reverse proxy headers correctly
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Enhanced security with a stronger secret key stored in env variable
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(32).hex())
# Configure session cookie security
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=1800  # 30 minutes
)

SCRIPTS_DIR = "scripts"
os.makedirs(SCRIPTS_DIR, exist_ok=True)

# Store API keys securely in environment variables
OBFUSCATOR_API_KEY = os.environ.get("OBFUSCATOR_API_KEY")
if not OBFUSCATOR_API_KEY:
    print("WARNING: OBFUSCATOR_API_KEY not set. Using fallback value for development only.")
    # This is just a placeholder - should use real API key in production
    OBFUSCATOR_API_KEY = hashlib.sha256(os.urandom(32)).hexdigest()[:36]

NEW_SCRIPT_URL = "https://api.luaobfuscator.com/v1/obfuscator/newscript"
OBFUSCATE_URL = "https://api.luaobfuscator.com/v1/obfuscator/obfuscate"

# Rate limiting configuration
RATE_LIMIT = {
    "window": 60,  # 1 minute
    "max_requests": 10  # 10 requests per minute
}
request_history = {}

# Set Content-Security-Policy headers
CSP_POLICY = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"

def rate_limit(f):
    """Decorator to implement rate limiting"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = request.remote_addr
        current_time = time.time()
        
        # Clean old entries
        for ip in list(request_history.keys()):
            request_history[ip] = [t for t in request_history[ip] if current_time - t < RATE_LIMIT["window"]]
            if not request_history[ip]:
                del request_history[ip]
        
        # Check rate limit
        if client_ip not in request_history:
            request_history[client_ip] = []
        
        if len(request_history[client_ip]) >= RATE_LIMIT["max_requests"]:
            return jsonify({"error": "Rate limit exceeded. Try again later."}), 429
        
        request_history[client_ip].append(current_time)
        return f(*args, **kwargs)
    
    return decorated_function

def set_security_headers(response):
    """Add security headers to response"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Content-Security-Policy'] = CSP_POLICY
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Referrer-Policy'] = 'same-origin'
    return response

@app.after_request
def after_request(response):
    """Apply security headers to all responses"""
    return set_security_headers(response)

def sanitize_filename(name):
    """Use werkzeug's secure_filename for better sanitization"""
    return secure_filename(name)

def validate_roblox_request():
    """Validate that request is coming from Roblox"""
    user_agent = request.headers.get("User-Agent", "").lower()
    
    # More comprehensive check for Roblox
    is_roblox = any(ua in user_agent for ua in ["roblox", "rbxapp", "robloxapp", "rbxproxy"])
    
    # Add additional validation based on headers or other characteristics
    # This could be expanded based on analysis of legitimate Roblox requests
    
    return is_roblox

def generate_access_token(script_id):
    """Generate a temporary access token for script access"""
    timestamp = str(int(time.time()))
    message = f"{script_id}:{timestamp}"
    signature = hmac.new(
        app.secret_key.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return f"{timestamp}:{signature}"

def validate_access_token(script_id, token):
    """Validate the access token"""
    try:
        timestamp, signature = token.split(":", 1)
        current_time = int(time.time())
        
        # Token expires after 5 minutes
        if current_time - int(timestamp) > 300:
            return False
        
        # Regenerate signature for comparison
        message = f"{script_id}:{timestamp}"
        expected_signature = hmac.new(
            app.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    except:
        return False

def obfuscate_lua_code(code):
    """Obfuscate Lua code with error handling and additional security"""
    try:
        # Add request timeout for security
        new_script_headers = {
            "apikey": OBFUSCATOR_API_KEY,
            "content-type": "text"
        }
        session_response = requests.post(
            NEW_SCRIPT_URL, 
            headers=new_script_headers, 
            data=code, 
            timeout=10
        )
        
        if session_response.status_code != 200:
            return {"error": f"API error: {session_response.status_code}"}, False
        
        session_data = session_response.json()
        if not session_data.get("sessionId"):
            return {"error": "Failed to create session"}, False

        session_id = session_data["sessionId"]

        obfuscate_headers = {
            "apikey": OBFUSCATOR_API_KEY,
            "sessionId": session_id,
            "content-type": "application/json"
        }

        # Enhanced obfuscation options
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

        obfuscate_response = requests.post(
            OBFUSCATE_URL, 
            headers=obfuscate_headers, 
            data=json.dumps(obfuscation_options),
            timeout=10
        )
        
        if obfuscate_response.status_code != 200:
            return {"error": f"Obfuscation API error: {obfuscate_response.status_code}"}, False
        
        obfuscate_data = obfuscate_response.json()
        if not obfuscate_data.get("code"):
            return {"error": "Failed to obfuscate code"}, False

        return {"obfuscated_code": obfuscate_data["code"]}, True

    except requests.exceptions.Timeout:
        return {"error": "Request to obfuscation service timed out"}, False
    except requests.exceptions.RequestException as e:
        return {"error": f"Request error: {str(e)}"}, False
    except Exception as e:
        return {"error": str(e)}, False

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/generate', methods=['POST'])
@rate_limit
def generate():
    # Validate MIME type
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
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

    # Return script URL with access token - this doesn't expose the internal structure
    return jsonify({"link": f"{request.host_url}l/{script_id}.lua"}), 200

@app.route('/l/<script_id>.lua')
def loader_script(script_id):
    # Validate script_id format to prevent path traversal
    if not re.match(r'^[a-f0-9]{32}$', script_id):
        return render_template("error.html", message="Invalid script identifier"), 400
    
    # Validate that request is from Roblox
    if not validate_roblox_request():
        return render_template("unauthorized.html"), 403
    
    # Generate access token for the script
    access_token = generate_access_token(script_id)
    script_id_clean = re.sub(r"[^a-zA-Z0-9]", "", script_id)
    
    # The loader now uses a token-based approach
    loader_code = f'''
local HttpService = game:GetService("HttpService")
local response = http.request({{
    Url = "{request.host_url}_internal/{script_id_clean}.lua?token={access_token}",
    Method = "GET"
}})

if response.Success and response.StatusCode == 200 then
    loadstring(response.Body)()
else
    warn("Failed to load script: " .. (response.StatusCode or "Unknown Error"))
end
'''.strip()
    
    return Response(loader_code, mimetype='text/plain')

@app.route('/_internal/<script_id>.lua')
def internal_script(script_id):
    # Validate script_id format
    if not re.match(r'^[a-f0-9]{32}$', script_id):
        return Response('-- Invalid script identifier', mimetype='text/plain'), 400
    
    # Validate access token
    token = request.args.get('token', '')
    if not validate_access_token(script_id, token):
        return Response('-- Access denied: Invalid or expired token', mimetype='text/plain'), 403
    
    # Validate that request is from Roblox
    if not validate_roblox_request():
        return Response('-- Access denied: Unauthorized source', mimetype='text/plain'), 403
    
    script_id_clean = re.sub(r"[^a-zA-Z0-9]", "", script_id)
    script_path = os.path.join(SCRIPTS_DIR, f"{script_id_clean}.lua")

    if not os.path.exists(script_path):
        return Response('-- Script not found', mimetype='text/plain'), 404

    with open(script_path, "r", encoding="utf-8") as f:
        return Response(f.read(), mimetype='text/plain')

@app.route('/api/obfuscate', methods=['POST'])
@rate_limit
def api_obfuscate():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    # Validate authorization
    api_key = request.headers.get('X-API-Key')
    if not api_key or not hmac.compare_digest(api_key, OBFUSCATOR_API_KEY):
        return jsonify({"error": "Unauthorized"}), 401

    script_content = request.json.get("script", "")
    if not script_content:
        return jsonify({"error": "No script provided"}), 400

    obfuscation_result, success = obfuscate_lua_code(script_content)

    if not success:
        return jsonify(obfuscation_result), 500

    return jsonify({"obfuscated_code": obfuscation_result["obfuscated_code"]}), 200

# Error handlers for common HTTP errors
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

# Redirect any attempts to access the scripts directory directly
@app.route('/scripts/<path:path>')
def block_scripts_access(path):
    return redirect(url_for('home'))

# Health check endpoint for monitoring
@app.route('/health')
def health_check():
    return jsonify({"status": "ok", "timestamp": time.time()}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    # Always run in production mode, never debug mode
    app.run(host="0.0.0.0", port=port, debug=False, ssl_context='adhoc')
