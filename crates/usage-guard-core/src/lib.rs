use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum TaskPhase {
    Analyze,
    Plan,
    Work,
    Verify,
    Complete,
    Failed,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum Strategy {
    SingleTurn,
    SingleAgent,
    BoundedLoop,
    PlanExecuteVerify,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct Policy {
    pub strategy: Strategy,
    pub context_budget_tokens: u32,
    pub max_actions: u16,
    pub max_model_turns: u16,
    pub max_retries: u16,
}

impl Policy {
    pub fn from_scores(complexity: u8, risk: u8) -> Self {
        match (complexity, risk) {
            (0..=2, 0..=3) => Self {
                strategy: Strategy::SingleTurn,
                context_budget_tokens: 8_000,
                max_actions: 6,
                max_model_turns: 2,
                max_retries: 1,
            },
            (0..=5, 0..=5) => Self {
                strategy: Strategy::SingleAgent,
                context_budget_tokens: 14_000,
                max_actions: 10,
                max_model_turns: 4,
                max_retries: 2,
            },
            (0..=7, 0..=7) => Self {
                strategy: Strategy::BoundedLoop,
                context_budget_tokens: 20_000,
                max_actions: 14,
                max_model_turns: 5,
                max_retries: 2,
            },
            _ => Self {
                strategy: Strategy::PlanExecuteVerify,
                context_budget_tokens: 28_000,
                max_actions: 16,
                max_model_turns: 6,
                max_retries: 2,
            },
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum CheckState {
    Unavailable,
    NotRun,
    Pass,
    Fail,
    NotNeeded,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct VerificationState {
    pub changed_files: u32,
    pub tests: CheckState,
    pub build: CheckState,
    pub lint: CheckState,
    pub typecheck: CheckState,
    pub browser: CheckState,
    pub diff_reviewed: bool,
    pub production_check_required: bool,
    pub production_checked: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum NextAction {
    Inspect,
    RunTests,
    RunTypecheck,
    RunBuild,
    RunLint,
    BrowserVerify,
    ReviewDiff,
    ProductionVerify,
    Done,
    Blocked,
}

fn pending(state: CheckState) -> bool {
    matches!(state, CheckState::NotRun)
}

fn failed(state: CheckState) -> bool {
    matches!(state, CheckState::Fail)
}

pub fn predict_next_action(v: &VerificationState) -> NextAction {
    if v.changed_files == 0 {
        return NextAction::Inspect;
    }
    if failed(v.tests) || failed(v.typecheck) || failed(v.build) || failed(v.lint) || failed(v.browser) {
        return NextAction::Blocked;
    }
    if pending(v.tests) {
        return NextAction::RunTests;
    }
    if pending(v.typecheck) {
        return NextAction::RunTypecheck;
    }
    if pending(v.build) {
        return NextAction::RunBuild;
    }
    if pending(v.lint) {
        return NextAction::RunLint;
    }
    if pending(v.browser) {
        return NextAction::BrowserVerify;
    }
    if !v.diff_reviewed {
        return NextAction::ReviewDiff;
    }
    if v.production_check_required && !v.production_checked {
        return NextAction::ProductionVerify;
    }
    NextAction::Done
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct Budget {
    pub actions_used: u16,
    pub model_turns_used: u16,
    pub retries_used: u16,
    pub policy: Policy,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct BudgetStatus {
    pub actions_remaining: u16,
    pub model_turns_remaining: u16,
    pub retries_remaining: u16,
    pub may_continue_model_work: bool,
}

impl Budget {
    pub fn status(self) -> BudgetStatus {
        let actions_remaining = self.policy.max_actions.saturating_sub(self.actions_used);
        let model_turns_remaining = self.policy.max_model_turns.saturating_sub(self.model_turns_used);
        let retries_remaining = self.policy.max_retries.saturating_sub(self.retries_used);
        BudgetStatus {
            actions_remaining,
            model_turns_remaining,
            retries_remaining,
            may_continue_model_work: actions_remaining > 0 && model_turns_remaining > 0,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn simple_policy_is_bounded() {
        let p = Policy::from_scores(1, 1);
        assert_eq!(p.strategy, Strategy::SingleTurn);
        assert_eq!(p.max_model_turns, 2);
    }

    #[test]
    fn hard_policy_uses_plan_execute_verify() {
        let p = Policy::from_scores(9, 8);
        assert_eq!(p.strategy, Strategy::PlanExecuteVerify);
        assert_eq!(p.max_actions, 16);
    }

    #[test]
    fn deterministic_checks_precede_diff_review() {
        let v = VerificationState {
            changed_files: 2,
            tests: CheckState::Pass,
            build: CheckState::NotRun,
            lint: CheckState::Unavailable,
            typecheck: CheckState::Pass,
            browser: CheckState::NotNeeded,
            diff_reviewed: false,
            production_check_required: false,
            production_checked: false,
        };
        assert_eq!(predict_next_action(&v), NextAction::RunBuild);
    }

    #[test]
    fn exhausted_model_budget_does_not_invent_capacity() {
        let policy = Policy::from_scores(4, 4);
        let status = Budget {
            actions_used: 3,
            model_turns_used: policy.max_model_turns,
            retries_used: 0,
            policy,
        }
        .status();
        assert!(!status.may_continue_model_work);
        assert!(status.actions_remaining > 0);
    }
}
