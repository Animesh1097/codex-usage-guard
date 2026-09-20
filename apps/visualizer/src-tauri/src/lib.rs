use serde::Serialize;
use serde_json::Value;
use std::{
    env, fs,
    path::{Path, PathBuf},
    sync::Mutex,
};

struct AppState {
    task_id: Mutex<Option<String>>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct TaskSnapshot {
    task_id: String,
    objective: String,
    status: String,
    phase: String,
    activity: String,
    task_kind: String,
    actions_used: u64,
    actions_limit: u64,
    turns_used: u64,
    turns_limit: u64,
    token_delta: Option<i64>,
    updated_at: Option<String>,
}

fn launch_task_id() -> Option<String> {
    let args: Vec<String> = env::args().collect();
    args.windows(2)
        .find(|pair| pair[0] == "--task-id")
        .map(|pair| pair[1].clone())
}

fn usage_guard_home() -> Option<PathBuf> {
    if let Some(path) = env::var_os("CODEX_USAGE_GUARD_DATA") {
        return Some(PathBuf::from(path));
    }
    env::var_os("USERPROFILE")
        .or_else(|| env::var_os("HOME"))
        .map(|home| PathBuf::from(home).join(".codex-usage-guard-data"))
}

fn read_state(task_id: &str) -> Result<Value, String> {
    let root = usage_guard_home().ok_or_else(|| "home directory unavailable".to_string())?;
    let path = root.join("tasks").join(format!("{task_id}.json"));
    let text = fs::read_to_string(&path)
        .map_err(|error| format!("cannot read {}: {error}", path.display()))?;
    serde_json::from_str(&text).map_err(|error| format!("invalid task state: {error}"))
}

fn str_at<'a>(value: &'a Value, path: &[&str]) -> Option<&'a str> {
    let mut cursor = value;
    for key in path {
        cursor = cursor.get(*key)?;
    }
    cursor.as_str()
}

fn u64_at(value: &Value, path: &[&str]) -> Option<u64> {
    let mut cursor = value;
    for key in path {
        cursor = cursor.get(*key)?;
    }
    cursor.as_u64()
}

fn i64_at(value: &Value, path: &[&str]) -> Option<i64> {
    let mut cursor = value;
    for key in path {
        cursor = cursor.get(*key)?;
    }
    cursor.as_i64()
}

fn snapshot_from_state(task_id: &str, state: &Value) -> TaskSnapshot {
    TaskSnapshot {
        task_id: task_id.to_string(),
        objective: str_at(state, &["objective"]).unwrap_or("").to_string(),
        status: str_at(state, &["status"]).unwrap_or("active").to_string(),
        phase: str_at(state, &["visual", "phase"]).unwrap_or("analyze").to_string(),
        activity: str_at(state, &["visual", "activity"]).unwrap_or("inspect").to_string(),
        task_kind: str_at(state, &["plan", "task_kind"]).unwrap_or("general").to_string(),
        actions_used: u64_at(state, &["counters", "actions"]).unwrap_or(0),
        actions_limit: u64_at(state, &["plan", "max_actions"]).unwrap_or(0),
        turns_used: u64_at(state, &["counters", "model_turns"]).unwrap_or(0),
        turns_limit: u64_at(state, &["plan", "max_model_turns"]).unwrap_or(0),
        token_delta: i64_at(state, &["usage", "delta", "tokens_delta"]),
        updated_at: str_at(state, &["updated_at"]).map(str::to_string),
    }
}

#[tauri::command]
fn get_task_snapshot(state: tauri::State<'_, AppState>) -> Result<TaskSnapshot, String> {
    let task_id = state
        .task_id
        .lock()
        .map_err(|_| "task state lock poisoned".to_string())?
        .clone()
        .ok_or_else(|| "launch with --task-id <id>".to_string())?;

    let raw = read_state(&task_id)?;
    Ok(snapshot_from_state(&task_id, &raw))
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(AppState {
            task_id: Mutex::new(launch_task_id()),
        })
        .invoke_handler(tauri::generate_handler![get_task_snapshot])
        .run(tauri::generate_context!())
        .expect("error while running Usage Guard visualizer");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn snapshot_exposes_only_visual_contract_fields() {
        let state: Value = serde_json::json!({
            "objective": "fix UI",
            "status": "active",
            "visual": {"phase": "work", "activity": "editing"},
            "plan": {"task_kind": "ui", "max_actions": 10, "max_model_turns": 4},
            "counters": {"actions": 3, "model_turns": 1},
            "usage": {"delta": {"tokens_delta": 1234}},
            "execution": {"requested_model": "hidden-from-visual-contract"}
        });
        let snapshot = snapshot_from_state("abc", &state);
        assert_eq!(snapshot.phase, "work");
        assert_eq!(snapshot.actions_used, 3);
        assert_eq!(snapshot.token_delta, Some(1234));
    }
}
