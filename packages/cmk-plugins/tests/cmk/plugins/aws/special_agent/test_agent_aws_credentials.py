#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The agent must report a broken credential chain, not crash on it.

The failing provider is injected the way a real deployment configures one: an AWS
config file pointing at a credential_process. No Checkmk code is patched.
"""

import stat
from pathlib import Path

import pytest

from cmk.plugins.aws.special_agent.agent_aws import agent_aws_main, parse_arguments

# Keyless: no --access-key-identity and no --secret, so boto3 walks the provider chain.
KEYLESS_ARGS = [
    "--hostname",
    "aws-host",
    "--piggyback-naming-convention",
    "ip_region_instance",
    "--region",
    "eu-central-1",
    "--service",
    "ec2",
]


def _write_credential_process(tmp_path: Path, script: str) -> Path:
    process = tmp_path / "credential_process.sh"
    process.write_text(script)
    process.chmod(process.stat().st_mode | stat.S_IEXEC)

    config = tmp_path / "aws_config"
    config.write_text(f"[default]\ncredential_process = {process}\n")
    return config


@pytest.fixture(name="failing_credential_process")
def _failing_credential_process(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point the boto3 credential chain at a provider that fails."""
    config = _write_credential_process(
        tmp_path, "#!/bin/sh\necho 'no credentials for you' >&2\nexit 1\n"
    )

    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.setenv("AWS_CONFIG_FILE", str(config))
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", str(tmp_path / "does_not_exist"))
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")


@pytest.mark.usefixtures("failing_credential_process")
def test_connection_test_reports_a_failing_credential_process(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = agent_aws_main(parse_arguments([*KEYLESS_ARGS, "--connection-test"]))

    assert exit_code == 2
    reported = capsys.readouterr().err
    assert "Connection failed with:" in reported
    # botocore names the provider it could not get credentials from.
    assert "custom-process" in reported


@pytest.mark.usefixtures("failing_credential_process")
def test_agent_run_writes_an_exceptions_section_for_a_failing_credential_process(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = agent_aws_main(parse_arguments(KEYLESS_ARGS))

    assert exit_code == 0
    assert "<<<aws_exceptions>>>" in capsys.readouterr().out


@pytest.fixture(name="missing_aws_profile")
def _missing_aws_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    """A profile that does not exist. boto3 raises in the Session constructor."""
    monkeypatch.setenv("AWS_PROFILE", "doesnotexist")
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")


@pytest.mark.usefixtures("missing_aws_profile")
def test_connection_test_reports_a_missing_profile(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The session constructor can fail too, not only the client call."""
    exit_code = agent_aws_main(parse_arguments([*KEYLESS_ARGS, "--connection-test"]))

    assert exit_code == 2
    assert "Connection failed with:" in capsys.readouterr().err


@pytest.mark.usefixtures("missing_aws_profile")
def test_agent_run_writes_an_exceptions_section_for_a_missing_profile(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = agent_aws_main(parse_arguments(KEYLESS_ARGS))

    assert exit_code == 0
    assert "<<<aws_exceptions>>>" in capsys.readouterr().out
