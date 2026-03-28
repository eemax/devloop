from devloop.models import Finding, FindingSeverity
from devloop.stop_conditions import blocking_findings, decide_round_stop


def test_stop_on_success_when_checks_pass_and_no_blockers() -> None:
    decision = decide_round_stop([], required_checks_pass=True, diff_changed=True, repeated_findings=False)
    assert decision.stop is True
    assert decision.status.value == "success"


def test_blocking_findings_filters_by_severity() -> None:
    findings = [
        Finding(id="1", severity=FindingSeverity.BLOCKING, title="A", evidence="A"),
        Finding(id="2", severity=FindingSeverity.MINOR, title="B", evidence="B"),
    ]

    blockers = blocking_findings(findings)

    assert len(blockers) == 1
    assert blockers[0].id == "1"
