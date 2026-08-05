#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
from collections.abc import Iterable
from contextlib import AbstractContextManager, ExitStack
from pathlib import Path

from tests.testlib.site import Site

# A throw-away special agent plugin whose ``commands_function`` yields *three*
# ``SpecialAgentCommand``s.  Its files live next to this test (see
# ``multicalltest_plugin``) and are copied into the site's ``local/`` tree to
# play the role of a third-party plugin.
_PLUGIN_SRC_FAMILY_DIR = "test_plugins/multicalltest_plugin"
_PLUGIN_FAMILY_DIR = "local/lib/python3/cmk_addons/plugins/multicalltest"


def test_special_agent_multiple_command_lines(site: Site) -> None:
    """A special agent yielding several commands must run all of them (SUP-29815).

    Before the fix the sources of the individual ``SpecialAgentCommand``s were
    deduplicated by their (identical) ident, so only the last command line was
    executed.  ``cmk -d`` must now dump the output of every command line.
    """
    host_name = "multicall-test-host"
    agent_path = f"{_PLUGIN_FAMILY_DIR}/libexec/agent_multicalltest"
    rule_mk = f"etc/check_mk/conf.d/{host_name}.mk"

    def _plugin_files() -> Iterable[AbstractContextManager[Path]]:
        root = Path(__file__).parent
        for src_file, dst_file in (
            ("server_side_calls/special_agent.py", "server_side_calls/special_agent.py"),
            ("rulesets/special_agent.py", "rulesets/special_agent.py"),
            # FYI: In the repo the Python file is required to have a `.py` extension,
            # but in the site's plugin directory its name has to match the plugin name exactly (i.e. no extension)
            ("libexec/agent_multicalltest.py", "libexec/agent_multicalltest"),
        ):
            yield site.copy_file(
                root / _PLUGIN_SRC_FAMILY_DIR / src_file, f"{_PLUGIN_FAMILY_DIR}/{dst_file}"
            )

    with ExitStack() as stack:
        for file in _plugin_files():
            stack.enter_context(file)

        site.run(["chmod", "+x", site.path(agent_path).as_posix()])

        # Configure a host that uses the special agent.
        site.openapi.hosts.create(host_name, attributes={"ipaddress": "127.0.0.1"})
        try:
            site.write_file(
                rule_mk,
                "special_agents['multicalltest'] = ["
                f"{{'id': '01', 'condition': {{'host_name': ['{host_name}']}}, 'value': {{}}}}"
                "]\n",
            )
            site.activate_changes_and_wait_for_core_reload()

            # Dump the raw agent data, which concatenates the output of every source.
            p = site.execute(
                ["cmk", "-d", host_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = p.communicate()
            assert p.returncode == 0, f"'cmk -d' failed: stdout={stdout!r} stderr={stderr!r}"

            # Every command line produced output (before the fix only "three" survived).
            for instance in ("one", "two", "three"):
                assert f"called_with={instance}" in stdout, (
                    f"special agent instance {instance!r} missing from dump:\n{stdout}"
                )
            assert stdout.count("<<<multicalltest>>>") == 3, stdout
        finally:
            if site.file_exists(rule_mk):
                site.delete_file(rule_mk)
            site.openapi.hosts.delete(host_name)
            site.activate_changes_and_wait_for_core_reload()
