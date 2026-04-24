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

    // Sort keys before serializing to guarantee a stable HMAC body
    // regardless of the order the agent sends fields
    let body = match sorted_json(&payload) {
        Some(b) => b,
        None => return false
    };

    let secret = get_secret();
    if secret.is_empty() {
        return false;
    }

    let mut mac = match HmacSha256::new_from_slice(&secret) {
        Ok(m) => m,
        Err(_) => return false
    };
    mac.update(body.as_bytes());

    let expected = hex::encode(mac.finalize().into_bytes());
    hmac::subtle::ConstantTimeEq::ct_eq(
        signature.as_bytes(),
        expected.as_bytes()
    ).into()
}

/// Serialize a JSON value with object keys sorted so the HMAC body is stable.
fn sorted_json(value: &Value) -> Option<String> {
    match value {
        Value::Object(map) => {
            let mut sorted: Vec<(&String, &Value)> = map.iter().collect();
            sorted.sort_by_key(|(k, _)| *k);
            let mut out = String::from("{");
            for (i, (k, v)) in sorted.iter().enumerate() {
                if i > 0 { out.push(','); }
                out.push_str(&serde_json::to_string(k).ok()?);
                out.push(':');
                out.push_str(&sorted_json(v)?);
            }
            out.push('}');
            Some(out)
        }
        _ => serde_json::to_string(value).ok()
    }
}
