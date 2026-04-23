use serde_json::Value;

// Simplified verifier for phase 2
// Full Ed25519 signature verification added in hardening phase
pub fn verify(request: &Value) -> bool {
    // For now check that request has required fields
    // and a signature field exists
    if request["action"].is_null() {
        return false;
    }
    if request["signature"].is_null() {
        return false;
    }
    // TODO: replace with real Ed25519 verification
    true
}