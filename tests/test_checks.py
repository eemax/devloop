import sys
from pathlib import Path

from devloop.checks import run_checks
from devloop.models import CheckResultStatus, CheckSpec


def test_run_checks_records_pass_and_fail(tmp_path: Path) -> None:
    checks = [
        CheckSpec(name="pass", command=f'{sys.executable} -c "raise SystemExit(0)"'),
        CheckSpec(name="fail", command=f'{sys.executable} -c "raise SystemExit(2)"'),
    ]

    results = run_checks(checks, tmp_path, required=True)

    assert [result.status for result in results] == [CheckResultStatus.PASS, CheckResultStatus.FAIL]
    assert results[1].exit_code == 2
    assert all(result.required for result in results)


def test_run_checks_marks_timeout_as_failure(tmp_path: Path) -> None:
    checks = [
        CheckSpec(
            name="slow",
            command=f'{sys.executable} -c "import time; time.sleep(2)"',
            timeout_secs=1,
        )
    ]

    results = run_checks(checks, tmp_path, required=False)

    assert results[0].exit_code == 124
    assert results[0].status == CheckResultStatus.NOT_RUN
    assert "timed out" in results[0].stderr
    assert results[0].required is False
