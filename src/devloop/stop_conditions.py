from __future__ import annotations

from devloop.models import FinalStatus, Finding, FindingSeverity, StopDecision


def decide_round_stop(
    unresolved_findings: list[Finding],
    required_checks_pass: bool,
    diff_changed: bool,
    repeated_findings: bool,
) -> StopDecision:
    if not diff_changed:
        return StopDecision(stop=True, status=FinalStatus.STALLED, reason="no material diff change in round")

    if repeated_findings:
        return StopDecision(stop=True, status=FinalStatus.STALLED, reason="audit findings repeated without progress")

    if required_checks_pass and not blocking_findings(unresolved_findings):
        return StopDecision(stop=True, status=FinalStatus.SUCCESS, reason="all required checks passed and no blocking findings remain")

    return StopDecision(stop=False, reason="continue to next round")


def blocking_findings(findings: list[Finding]) -> list[Finding]:
    return [finding for finding in findings if finding.severity == FindingSeverity.BLOCKING]
