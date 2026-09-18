from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from guard.classifier import classify_task
from guard.compressor import compress_test_output, estimate_tokens


def main() -> int:
    fixtures = json.loads((ROOT / "benchmarks" / "fixtures.json").read_text(encoding="utf-8"))
    failures: list[str] = []

    for item in fixtures:
        plan = classify_task(item["task"], repo_path="/definitely/not/a/repo")
        if "min_complexity" in item and plan.complexity < item["min_complexity"]:
            failures.append(f"{item['name']}: complexity {plan.complexity} below {item['min_complexity']}")
        if "max_complexity" in item and plan.complexity > item["max_complexity"]:
            failures.append(f"{item['name']}: complexity {plan.complexity} above {item['max_complexity']}")
        if plan.agent_profile != item["profile"]:
            failures.append(f"{item['name']}: profile {plan.agent_profile} != {item['profile']}")
        if plan.preferred_model != item["model"]:
            failures.append(f"{item['name']}: model {plan.preferred_model} != {item['model']}")

    noisy = "\n".join([f"PASS test_{i}" for i in range(1000)] + ["FAIL payment", "expected 200 received 500"])
    compact = compress_test_output(noisy)
    before = estimate_tokens(noisy)
    after = estimate_tokens(compact)
    reduction = round((1 - after / before) * 100, 1) if before else 0.0
    if after >= before:
        failures.append("test output compression did not reduce estimated context")

    result = {
        "fixtures": len(fixtures),
        "compression_estimate": {
            "before": before,
            "after": after,
            "reduction_pct": reduction,
        },
        "failures": failures,
    }
    print(json.dumps(result, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
