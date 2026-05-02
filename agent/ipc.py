import socket
import json
import os
import time
import hashlib
import hmac

# Shared secret between agent and helper
# Generated at first run and stored in /etc/aios/secret
from config import SOCKET_PATH, DRY_RUN, IPC_SECRET_PATH
SECRET_PATH = IPC_SECRET_PATH

def get_secret() -> bytes:
    if os.path.exists(SECRET_PATH):
        with open(SECRET_PATH, "rb") as f:
            return f.read()
    # Generate and store on first run
    secret = os.urandom(32)
    os.makedirs("/etc/aios", exist_ok=True)
    with open(SECRET_PATH, "wb") as f:
        f.write(secret)
    os.chmod(SECRET_PATH, 0o600)
    return secret

def sign_request(payload: dict) -> dict:
    secret = get_secret()
    body = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
    signature = hmac.new(secret, body, hashlib.sha256).hexdigest()
    payload["signature"] = signature
    return payload

def verify_signature(payload: dict) -> bool:
    secret = get_secret()
    signature = payload.pop("signature", None)
    if not signature:
        return False
    body = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
    payload["signature"] = signature  # restore
    return hmac.compare_digest(signature, expected)

def send_action(action: dict) -> dict:
    if DRY_RUN:
        print(f"[DRY RUN] {json.dumps(action)}")
        return {"success": True, "message": "dry_run"}

    signed = sign_request(action)

    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(SOCKET_PATH)
        sock.sendall((json.dumps(signed) + "\n").encode())

        response = b""
        while True:
            chunk = sock.recv(1024)
            if not chunk:
                break
            response += chunk
            if b"\n" in response:
                break

        sock.close()
        return json.loads(response.decode().strip())

    except FileNotFoundError:
        return {"success": False, "message": "helper socket not found"}
    except socket.timeout:
        return {"success": False, "message": "helper timeout"}
    except Exception as e:
        return {"success": False, "message": str(e)}

def send_actions(actions: list) -> list:
    results = []
    for action in actions:
        result = send_action(action)
        results.append({
            "action": action,
            "result": result
        })
        # Small delay between actions to avoid flooding helper
        time.sleep(0.05)
    return results