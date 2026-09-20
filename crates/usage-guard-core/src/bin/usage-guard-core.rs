use std::{env, process};
use usage_guard_core::{predict_next_action, Policy, VerificationState};

fn print_json<T: serde::Serialize>(value: &T) {
    println!("{}", serde_json::to_string(value).expect("serialize output"));
}

fn usage() -> ! {
    eprintln!("usage-guard-core policy <complexity> <risk>");
    eprintln!("usage-guard-core next-action <verification-state-json>");
    process::exit(2);
}

fn main() {
    let args: Vec<String> = env::args().collect();
    match args.get(1).map(String::as_str) {
        Some("policy") => {
            let complexity = args.get(2).and_then(|v| v.parse::<u8>().ok()).unwrap_or_else(|| usage());
            let risk = args.get(3).and_then(|v| v.parse::<u8>().ok()).unwrap_or_else(|| usage());
            print_json(&Policy::from_scores(complexity, risk));
        }
        Some("next-action") => {
            let raw = args.get(2).unwrap_or_else(|| usage());
            let state: VerificationState = serde_json::from_str(raw).unwrap_or_else(|error| {
                eprintln!("invalid verification state: {error}");
                process::exit(2);
            });
            print_json(&predict_next_action(&state));
        }
        _ => usage(),
    }
}
