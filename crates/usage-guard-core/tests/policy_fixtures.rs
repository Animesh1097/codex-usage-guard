use serde::Deserialize;
use usage_guard_core::{Policy, Strategy};

#[derive(Debug, Deserialize)]
struct Fixture {
    name: String,
    complexity: u8,
    risk: u8,
    strategy: Strategy,
    max_actions: u16,
    max_model_turns: u16,
}

#[test]
fn shared_policy_fixtures_match() {
    let raw = include_str!("../../../fixtures/policy_cases.json");
    let cases: Vec<Fixture> = serde_json::from_str(raw).expect("valid fixture JSON");
    for case in cases {
        let policy = Policy::from_scores(case.complexity, case.risk);
        assert_eq!(policy.strategy, case.strategy, "strategy: {}", case.name);
        assert_eq!(policy.max_actions, case.max_actions, "actions: {}", case.name);
        assert_eq!(policy.max_model_turns, case.max_model_turns, "turns: {}", case.name);
    }
}
