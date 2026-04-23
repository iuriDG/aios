mod verifier;
mod allowlist;
mod executor;
mod protected;

use std::io::{BufRead, BufReader, Write};
use std::os::unix::net::UnixListener;
use std::fs;
use serde_json::Value;

const SOCKET_PATH: &str = "/run/aios/helper.sock";

fn main() {
    // Create socket directory if it doesnt exist
    fs::create_dir_all("/run/aios").expect("Failed to create /run/aios");

    // Remove stale socket
    let _ = fs::remove_file(SOCKET_PATH);

    let listener = UnixListener::bind(SOCKET_PATH)
        .expect("Failed to bind socket");

    println!("aios-helper listening on {}", SOCKET_PATH);

    for stream in listener.incoming() {
        match stream {
            Ok(mut stream) => {
                let mut reader = BufReader::new(stream.try_clone().unwrap());
                let mut line = String::new();

                if reader.read_line(&mut line).is_ok() {
                    let response = handle_request(line.trim());
                    let _ = stream.write_all(response.as_bytes());
                    let _ = stream.write_all(b"\n");
                }
            }
            Err(e) => {
                eprintln!("Connection error: {}", e);
            }
        }
    }
}

fn handle_request(raw: &str) -> String {
    // Parse JSON
    let request: Value = match serde_json::from_str(raw) {
        Ok(v) => v,
        Err(_) => return response(false, "invalid JSON")
    };

    // Verify signature
    if !verifier::verify(&request) {
        eprintln!("Rejected unsigned or forged request");
        return response(false, "signature verification failed");
    }

    // Extract action
    let action = match request["action"].as_str() {
        Some(a) => a,
        None => return response(false, "missing action field")
    };

    // Check allowlist
    if !allowlist::is_allowed(action) {
        eprintln!("Rejected action not on allowlist: {}", action);
        return response(false, "action not on allowlist");
    }

    // Check protected processes
    if let Some(pid) = request["pid"].as_i64() {
        if protected::is_protected(pid as i32) {
            eprintln!("Rejected action on protected PID: {}", pid);
            return response(false, "target is protected process");
        }
    }

    // Execute
    match executor::execute(&request) {
        Ok(msg) => response(true, &msg),
        Err(e) => response(false, &e.to_string())
    }
}

fn response(success: bool, message: &str) -> String {
    serde_json::json!({
        "success": success,
        "message": message
    }).to_string()
}