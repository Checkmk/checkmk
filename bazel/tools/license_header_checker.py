#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import pathlib
import re
import sys

GPL = r"""# Copyright \(C\) \d{4} Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk \(https://checkmk.com\). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package."""

ENTERPRISE = r"""# Copyright \(C\) \d{4} Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk \(https://checkmk.com\). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package."""

ENTERPRISE_HEADER = re.compile(rf"#!/usr/bin/env python3\n{ENTERPRISE}")
ENTERPRISE_HEADER_NO_SHEBANG = re.compile(rf"{ENTERPRISE}")
ENTERPRISE_HEADER_CODING = re.compile(
    rf"""#!/usr/bin/env python3
# -\*- coding: utf-8 -\*-
{ENTERPRISE}"""
)

ENTERPRISE_HEADER_ALERT_HANDLERS = re.compile(
    rf"""#!/usr/bin/env python3
# .+

{ENTERPRISE}"""
)

ENTERPRISE_HEADER_NOTIFICATION = re.compile(
    rf"""#!/usr/bin/env python3
# .+(\n# Bulk: (yes|no))?

{ENTERPRISE}
"""
)


OMD_HEADER = re.compile(rf"#!/omd/versions/###OMD_VERSION###/bin/python3\n{GPL}")

GPL_HEADER = re.compile(rf"#!/usr/bin/env (python3|-S python3 -P)\n{GPL}")
GPL_HEADER_NO_SHEBANG = re.compile(rf"{GPL}")

GPL_HEADER_NOTIFICATION = re.compile(
    rf"""#!/usr/bin/env python3
# .+(\n# Bulk: (yes|no))?

{GPL}
"""
)


ignored_files = [
    "packages/cmk-notification-plugins/cmk/notification_plugins/ilert.py",
    "packages/cmk-notification-plugins/cmk/notification_plugins/signl4.py",
    "tests/integration_redfish/mockup-server/redfishMockupServer.py",
    "tests/integration_redfish/mockup-server/rfSsdpServer.py",
    # Remove when CMK-31227 is implemented
    "packages/cmk-agent-receiver/cmk/agent_receiver/relay/api/__init__.py",
    "packages/cmk-agent-receiver/cmk/agent_receiver/relay/api/routers/relays/handlers/cert_retriever.py",
    "packages/cmk-agent-receiver/cmk/testlib/agent_receiver/schema.py",
    "packages/cmk-agent-receiver/tests/component/relay/test_activate_config.py",
    "packages/cmk-agent-receiver/tests/component/relay/test_cert_refresh.py",
    "packages/cmk-agent-receiver/tests/component/relay/test_create_task_unknown_relay.py",
    "packages/cmk-agent-receiver/tests/component/relay/test_forward_monitoring_data.py",
    "packages/cmk-agent-receiver/tests/component/relay/test_get_tasks_should_not_fail.py",
    "packages/cmk-agent-receiver/tests/unit/agent_receiver/relay/test_cert_retriever.py",
    "packages/cmk-agent-receiver/tests/unit/testlib/__init__.py",
]

# Similar logic to our partial GitHub sync approach. Both select enterprise files or directories
# based on their name.
enterprise_names = [
    "non-free",
    "nonfree",
    "pro",
    "ultimate",
    "ultimatemt",
    "cloud",
]


notification_dirs = [
    "notifications/",
    "packages/cmk-notification-plugins/notifications/",
    "non-free/packages/cmk-notification-plugins-nonfree/notifications/",
]


def is_notification_file(path: str) -> bool:
    return any(path.startswith(d) for d in notification_dirs)


def needs_enterprise_license(path: str) -> bool:
    parts = path.split("/")
    if any(p for p in enterprise_names if p in parts):
        return True

    return False


def get_file_header(path: str, length: int = 30) -> str:
    with open(path) as file:
        head = [file.readline() for x in range(length)]
        return "".join(head)


def check_for_license_header_violation(file_path: str) -> str | None:
    if file_path.startswith("non-free/packages/cmk-update-agent/cmk_update_agent.py"):
        if not ENTERPRISE_HEADER_CODING.match(get_file_header(file_path, length=5)):
            return "enterprise header with coding not matching"
    elif file_path.startswith("omd/non-free/packages/alert-handling/alert_handlers/"):
        if not ENTERPRISE_HEADER_ALERT_HANDLERS.match(get_file_header(file_path, length=8)):
            return "enterprise header with alert handler not matching"
    elif is_notification_file(file_path) and needs_enterprise_license(file_path):
        if not ENTERPRISE_HEADER_NOTIFICATION.match(get_file_header(file_path, length=10)):
            return "enterprise header with notification not matching"
    elif needs_enterprise_license(file_path):
        header = get_file_header(file_path, length=4)
        if not (ENTERPRISE_HEADER.match(header) or ENTERPRISE_HEADER_NO_SHEBANG.match(header)):
            return "enterprise header not matching"
    elif file_path in ("omd/packages/omd/omd.bin.py", "omd/packages/omd/omd_site_user.py"):
        if not OMD_HEADER.match(get_file_header(file_path, length=23)):
            return "omd gpl license header not matching"
    elif is_notification_file(file_path):
        if not GPL_HEADER_NOTIFICATION.match(get_file_header(file_path, length=10)):
            return "gpl header with notification not matching"
    else:
        header = get_file_header(file_path, length=4)
        if not (GPL_HEADER.match(header) or GPL_HEADER_NO_SHEBANG.match(header)):
            return "gpl header not matching"
    return None


def write_sarif_output(machine_path: str, violations: list[tuple[str, str]]) -> None:
    results = [
        {
            "ruleId": "license-header",
            "level": "error",
            "message": {"text": f"{src_path}: {reason}"},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": src_path,
                        }
                    }
                }
            ],
        }
        for src_path, reason in violations
    ]
    sarif = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "LicenseHeaderCheck",
                        "rules": [
                            {
                                "id": "license-header",
                                "shortDescription": {
                                    "text": "License header must be present and correct"
                                },
                            }
                        ],
                    }
                },
                "results": results,
            }
        ],
    }
    with open(machine_path, "w") as f:
        json.dump(sarif, f, indent=2)


def write_human_output(human_path: str, violations: list[tuple[str, str]]) -> None:
    if violations:
        lines = [f"  {src_path}: {res}" for src_path, res in violations]
        human_content = "LICENSE HEADER VIOLATIONS:\n" + "\n".join(lines) + "\n"
    else:
        human_content = "No license header violations found."
    with open(human_path, "w") as f:
        f.write(human_content)


def main() -> int:
    if len(sys.argv) < 6:
        print(
            f"Usage: {sys.argv[0]} <human_out_path> <machine_out_path> <human_exit_code_path> "
            f"<machine_exit_code_path> <source_file>...",
            file=sys.stderr,
        )
        return 2

    human_out_path, machine_out_path, human_exit_code_path, machine_exit_code_path, *src_paths = (
        sys.argv[1:]
    )

    violations = []
    for src_path in src_paths:
        if src_path in ignored_files:
            continue
        res = check_for_license_header_violation(src_path)
        if res:
            violations.append((str(pathlib.Path(src_path).resolve()), res))

    write_sarif_output(machine_out_path, violations)
    write_human_output(human_out_path, violations)

    exit_code = 1 if violations else 0

    if human_exit_code_path:
        with open(human_exit_code_path, "w") as f:
            f.write(str(exit_code))
    if machine_exit_code_path:
        with open(machine_exit_code_path, "w") as f:
            f.write(str(exit_code))

    fail_on_violation = not (human_exit_code_path or machine_exit_code_path)
    if fail_on_violation and violations:
        print(open(human_out_path).read(), file=sys.stderr)

    return 0 if not fail_on_violation else exit_code


if __name__ == "__main__":
    sys.exit(main())
