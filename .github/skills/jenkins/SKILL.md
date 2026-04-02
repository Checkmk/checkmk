---
name: jenkins
description: Interacts with the Jenkins CI to get build and test job results
---

# Diagnosing a CI failure

Always start here — stages, test failures, and sub-job URLs in one call:

```bash
jenkins_build_data.py <URL> --include=stages,tests --failed-only
```

Drill into a triggered sub-job (shown as `Job: <url>` in stage output):

```bash
jenkins_build_data.py <triggered-job-url> --include=console,tests
```

Full console (default shows last 100 lines):

```bash
jenkins_build_data.py <URL> --include=full-console
```

Poll a running build:

```bash
jenkins_build_data.py <URL> --include=stages,tests --poll --poll-interval=60
```

Do NOT use curl — the tool handles auth, stage correlation, and test parsing.

# Downloading artifacts

Always use `/tmp/jenkins-artifacts` as the download directory:

```bash
jenkins_build_data.py <url> --download "<artifact>" --download-dir /tmp/jenkins-artifacts
```

# Parsing of the downloaded json

Prefer `jq` over `python3` commands.

# Playwright trace analysis for failed GUI E2E tests

When a GUI E2E test fails, a Playwright trace zip is often available as a build artifact.

## 1. Find and download the trace

List artifacts to locate the trace (look for files matching `*trace*` or `*.zip`):

```bash
jenkins_build_data.py <url> --include=artifacts
```

Download it:

```bash
jenkins_build_data.py <url> --download "<artifact-path>" --download-dir /tmp/jenkins-artifacts
```

## 2. Analyze the trace with playwright-trace-analyzer

`playwright-trace-analyzer` is a CLI tool that inspects trace zips without a browser.

Before using it, verify it is installed:

```bash
playwright-trace-analyzer --version
```

If the command is not found, ask the user to install it:

```
uv tool install playwright-trace-analyzer
```

Get a high-level overview first:

```bash
playwright-trace-analyzer summary /tmp/jenkins-artifacts/<trace>.zip
```

Then drill into the actions to find where it failed:

```bash
playwright-trace-analyzer actions /tmp/jenkins-artifacts/<trace>.zip
```

Check network requests if the failure may be API-related:

```bash
playwright-trace-analyzer network /tmp/jenkins-artifacts/<trace>.zip
```

Check browser console errors:

```bash
playwright-trace-analyzer console /tmp/jenkins-artifacts/<trace>.zip
```

# Marking a build to keep forever

To prevent Jenkins from garbage-collecting a build (e.g. to preserve evidence of a flaky test), use the `toggleLogKeep` API endpoint. Auth is via `~/.netrc` (same as `jenkins_build_data.py`):

```python
python3 -c "
import netrc, urllib.request, base64
n = netrc.netrc()
login, _, password = n.authenticators('ci.lan.tribe29.com')
url = '<BUILD_URL>/toggleLogKeep'
req = urllib.request.Request(url, method='POST', data=b'')
credentials = base64.b64encode(f'{login}:{password}'.encode()).decode()
req.add_header('Authorization', f'Basic {credentials}')
resp = urllib.request.urlopen(req)
print(f'Status: {resp.status}')
"
```

Replace `<BUILD_URL>` with the full Jenkins build URL (e.g. `https://ci.lan.tribe29.com/job/checkmk/job/master/.../123`). This is a toggle — calling it again removes the "keep forever" flag.

Do NOT use `curl` with `$JENKINS_API_TOKEN` — it won't work. Use `~/.netrc` credentials with Basic auth as shown above.

# In case the commands jenkins_build_data.py is missing

Ask the user to clone the zeug_cmk git repository and add it to their PATH.
See also: https://wiki.lan.checkmk.net/x/4zBSCQ
