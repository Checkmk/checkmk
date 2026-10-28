# Veeam special agent system tests

`test_veeam_special_agent.py` sets up the monitoring of a Veeam Backup & Replication
server with the Veeam special agent, as a user would, and checks the result: the
services of the backup server and of a machine it protects, their states, summaries
and details, the host labels, and the HW/SW inventory. The special agent connects as
the Veeam Administrator.

`test_veeam_special_agent_viewer.py` does the same with a Veeam user that has only the
Veeam Backup Viewer role. It checks only what differs from the Administrator: the
services a Viewer may read are still there, those requiring the Administrator are not,
and the _Check_MK_ service warns about exactly the sections the Viewer was denied.

`conftest.py` holds the setup both share; each test module names its Veeam user in a
`veeam_account` fixture.

By default the tests run against a mocked Veeam server (`mock_vbr.py`), which replays
the REST API responses recorded from the lab server as the respective user
(`recorded_admin_responses.json`, `recorded_viewer_responses.json`). During manual
testing sessions, or on demand, they also run against the lab server itself.

## Run against the mock

```bash
pytest tests/system/singlesite/veeam --log-cli-level=INFO
```

The mock listens on a free port on `127.0.0.1` and accepts only the user and password
the test configures. Timestamps in the recorded responses are moved forward by the time
passed since the recording, so ages ("last backup 12 hours ago") stay what they were.

## Run against a real server

Name the server and the passwords of the Veeam users `Administrator`
(`VEEAM_SERVER_PASSWORD`) and `veeam-viewer` (`VEEAM_VIEWER_PASSWORD`) in the
environment; the mock is then not started. A test module whose password is missing
fails in its setup.

```bash
printf "Administrator password: " && read -rs VEEAM_SERVER_PASSWORD && echo && export VEEAM_SERVER_PASSWORD
printf "Viewer password: " && read -rs VEEAM_VIEWER_PASSWORD && echo && export VEEAM_VIEWER_PASSWORD
VEEAM_SERVER_ADDRESS=<server address> pytest tests/system/singlesite/veeam --log-cli-level=INFO
```

This also checks what the mock cannot: the login against the real server, its TLS
connection and the timing of a real run. The expected values in the test must match
the server's current state, not only the recording; a mismatch shows that the server
changed.

How to set up a real Veeam instance is described in Confluence:
[How to set up Veeam monitoring](https://checkmk-int.atlassian.net/wiki/spaces/DEV/pages/256245864/How+to+set+up+Veeam+monitoring).

## Record new responses

Record new responses when a run against the real server reveals a real change in its
API responses, for example after a Veeam update, and the special agent's resulting new
behavior is expected. The mock then replays the changed responses, and the expected
values in the test have to be updated to match.

The recording script is kept in the qa-test-data repository, checked out at
`tests/qa-test-data`, as `qa_utils/record_veeam_responses.py`. Run it from the
repository root, with the dev venv:

```bash
python3 tests/qa-test-data/qa_utils/record_veeam_responses.py --address <server address> --user Administrator --recording-file tests/system/singlesite/veeam/recorded_admin_responses.json
python3 tests/qa-test-data/qa_utils/record_veeam_responses.py --address <server address> --user veeam-viewer --recording-file tests/system/singlesite/veeam/recorded_viewer_responses.json
```

It asks for the password, runs the special agent once against the server, and writes
every response it gets to the given file. The login response is not saved, as it holds
a live access token. If the agent fails, nothing is written.

Before committing new recordings:

- Format them with `bazel run //:format tests/system/singlesite/veeam/`, so that
  `git diff` shows only real changes.
- Review them: they contain the server's host names, addresses and license holder.
- Check `git diff` of the recordings to see what changed on the server, and update
  the expected values at the top of both tests accordingly: the `BACKUP_SERVER_*`
  constants and the `EXPECTED_*_SERVICES` tables, and the host names in `helpers.py`.
- Run the tests against the mock and against the lab.
