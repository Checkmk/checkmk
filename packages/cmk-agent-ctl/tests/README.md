# Agent controller tests

Tests for the Checkmk agent controller, `cmk-agent-ctl`, and for how the agent package deploys it
under systemd. Only the Rust tests live in this directory. The others sit with the code they test,
or in the system test suites at the repository root.

## Documentation

- [`docs/ci-jobs.md`](docs/ci-jobs.md): which CI jobs exercise the controller, triggered by which
  development stage, on which kind of node.
- [`docs/test-systems.md`](docs/test-systems.md): the containers and nodes the tests run on, the
  systemd test container, and what it requires from the node.
- [`../docs/non-free/tech_design/updater_in_controller.md`](../docs/non-free/tech_design/updater_in_controller.md):
  the tech design of the agent updater in the controller.
- [`../docs/non-free/tests/`](../docs/non-free/tests/): the test plans.

## Test levels

| Level       | What                                                                                  | Where                                                                                         | Bazel target or entry point                                                 |
| :---------- | :------------------------------------------------------------------------------------ | :-------------------------------------------------------------------------------------------- | :-------------------------------------------------------------------------- |
| Unit        | The controller's library, `#[cfg(test)]` modules                                      | `src/`                                                                                        | `//packages/cmk-agent-ctl:cmk-agent-ctl-lib-internal`                       |
| Unit        | The bakery plugin that writes the controller's configuration                          | `tests/unit/cmk/base/nonfree/pro/plugins/bakery/test_agent_controller.py`                     | `bazel test` in the unit tree                                               |
| Unit        | The ruleset for the controller's options                                              | `tests/unit/cmk/plugins/generic_agent_options/rulesets/test_agent_controller.py`              | `bazel test` in the unit tree                                               |
| Unit        | The check plug-in for `cmk-agent-ctl status`                                          | `tests/unit/cmk/plugins/checkmk/agent_based/test_cmk_agent_ctl_status.py`                     | `bazel test` in the unit tree                                               |
| Unit        | The Windows agent's side of the controller                                            | `agents/wnx/watest/test-agent_controller.cpp`                                                 | `watest` on Windows, `//agents/wnx:watest-wine` under Wine, tagged `manual` |
| Integration | The built controller: CLI, pull mode, status                                          | `tests/test_cli.rs`, `tests/test_pull.rs`, `tests/test_status.rs`, helpers in `tests/common/` | `//packages/cmk-agent-ctl:cmk-agent-ctl-lib-external`                       |
| Integration | The Rust unit and integration tests above, cross-built for Windows and run under Wine | as above                                                                                      | `//packages/cmk-agent-ctl:cmk-agent-ctl-tests-wine`, tagged `manual`        |
| Integration | The `install-agent` mode, with stand-ins for `dpkg` and `rpm`                         | `tests/scripts/smoke-install-agent.sh`                                                        | `//packages/cmk-agent-ctl:smoke_install_agent`                              |
| System      | The deployment of the site's agent package on a host with systemd                     | `tests/system/agent_updates/`                                                                 | `tests/run_tests.sh test-system-agent-updates-docker`                       |
| System      | Registration and status against real sites                                            | `tests/system/multisite/agents/`, `tests/system/multisite/controller_site_interactions/`      | `tests/run_tests.sh test-system-multisite-docker`                           |

Several other system suites install the agent as a prerequisite, through the helpers in
`tests/testlib/system/agent.py`.

The targets tagged `manual` are left out of `bazel test //...`, so change validation does not run
them. [`docs/ci-jobs.md`](docs/ci-jobs.md) names the jobs that do.

## Running the tests

**Rust, Linux and Wine:**

```bash
bazel test //packages/cmk-agent-ctl/...                       # Linux
bazel test //packages/cmk-agent-ctl:cmk-agent-ctl-tests-wine   # Windows, under Wine
```

**System, agent updates:** the cases install the agent and change its registrations on the machine
they run on, so they run in a container:

```bash
tests/run_tests.sh test-system-agent-updates-docker
```

The suite needs a host that runs systemd and that it may change. The `-docker` target provides
such a host, because it boots systemd as PID 1 in the test container.
[`docs/test-systems.md`](docs/test-systems.md) explains how to choose the version and the
distribution, and how to open a shell in that container.

## Maintenance

The documents under `docs/` are the maintained overview of the controller's test setup
(CMK-40693, CMK-40696):

- Changing the CI wiring (job scripts under `buildscripts/scripts/`, `stages.yml`, the `run`
  script here) → update [`docs/ci-jobs.md`](docs/ci-jobs.md) in the same change.
- Changing a test container or the nodes it needs → update
  [`docs/test-systems.md`](docs/test-systems.md).
- Open questions are marked as `TODO` comments inside the documents. Resolve them when the answer
  is known.
