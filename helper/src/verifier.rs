use serde_json::Value;
use std::fs;
use hmac::{Hmac, Mac};
use sha2::Sha256;
use hex;

type HmacSha256 = Hmac<Sha256>;

const SECRET_PATH: &str = "/etc/aios/ipc.secret";

fn get_secret() -> Vec<u8> {
    fs::read(SECRET_PATH).unwrap_or_default()
}

pub fn verify(request: &Value) -> bool {
    let signature = match request["signature"].as_str() {
        Some(s) => s.to_string(),
        None => return false
    };

    // Rebuild payload without signature field
    let mut payload = request.clone();
    if let Some(obj) = payload.as_object_mut() {
        obj.remove("signature");
    }

    // Sort keys and serialize
    let body = match serde_json::to_string(&payload) {
        Ok(b) => b,
        Err(_) => return false
    };

    let secret = get_secret();
    if secret.is_empty() {
        return false;
    }

    let mut mac = HmacSha256::new_from_slice(&secret)
        .expect("HMAC init failed");
    mac.update(body.as_bytes());

    let expected = hex::encode(mac.finalize().into_bytes());
    hmac::subtle::ConstantTimeEq::ct_eq(
        signature.as_bytes(),
        expected.as_bytes()
    ).into()
}