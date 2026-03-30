# cmk-dev-deploy: Known Issues

Issues documented here are real but not yet fixed. Each has a workaround.

---

### `fuser -km` kills processes during overlay teardown

**File:** `site/overlay.py`

When `umount` fails (a process has an open file under the site directory),
the tool runs `fuser -km` which sends SIGKILL to every process holding a
file open under the mount point — including editors, terminals, or `tail -f`.

**Trigger:** `--full` or `--purge` while any process has a file open under the
site directory.

**Workaround:** Close editors and shells that have site files open before
running `--full` or `--purge`.

**Fix:** Replace `fuser -km` with `fuser -m` (list only), show the process
list to the user, and ask for confirmation before killing.

---

### `omd stop` timeout too short for overlay mount

**File:** `core/timeouts.py` (`OVERLAY_CMD = 60`), `site/overlay.py`

The site is stopped with a 60-second timeout before mounting the overlay.
A site with a hung CMC process won't stop in 60 seconds. The mount proceeds
against a partially-running site.

**Trigger:** Any site with a stuck service (CMC, Apache with hung workers).

**Workaround:** Manually `omd stop <site>` before running cmk-dev-deploy.

**Fix:** Check that `omd stop` actually succeeded (exit code) before
proceeding with the mount. On timeout, abort with a clear message instead of
mounting over a live site.

---

### `.mo` files pollute the source tree

**File:** `deployers/config_deployer.py` — `_compile_and_deploy_locale()`

The locale deployer runs `msgfmt` which writes compiled `.mo` files alongside
the `.po` source files in the repo working tree. This makes `git status` dirty
and triggers false-positive change detection on the next deploy cycle.

**Trigger:** Any deploy that includes locale changes.

**Workaround:** Add `*.mo` to `.gitignore` (if not already present), or
manually `git checkout -- locale/` after deploys.

**Fix:** Write `.mo` files to a temp directory, deploy from there, then clean
up. Never write build artifacts into the source tree.

---

### Shared `/var/tmp/cmk-dev-deploy` collides across users

**File:** `site/overlay.py`, `state/deploy_state.py`

The overlay upper layer and deploy state are stored in
`/var/tmp/cmk-dev-deploy/<site_name>/`. This path is keyed by site name only,
not by user. Two developers on the same shared dev server deploying to sites
with the same name overwrite each other's overlay and state.

**Trigger:** Two users on the same machine with a site of the same name.

**Workaround:** Use unique site names per developer.

**Fix:** Include the deploying user's UID in the path, e.g.,
`/var/tmp/cmk-dev-deploy/<uid>/<site_name>/`.

---

### Stale site-packages cache in watch mode

**File:** `deployers/_site_python.py` — `_discover_site_packages_cached()`

The LRU cache for the site's Python `site-packages` path is never invalidated.
In watch mode (long-running), if the site Python environment changes (version
bump, new venv), the cached path is used for the rest of the session. Files
deploy to the wrong location.

**Trigger:** Changing the site's Python environment while watch mode is running.

**Workaround:** Restart cmk-dev-deploy after any change to the site's Python
environment.

**Fix:** Invalidate the cache when the site's Python symlink changes, or add a
TTL to the LRU cache.

---

### No upper bound on `--jobs`

**File:** `cli.py` — `parse_args()`

`--jobs` is clamped to `min=1` but has no upper bound. A very large value
creates that many threads in the ThreadPoolExecutor.

**Trigger:** `cdd --jobs 9999` (or any high value).

**Workaround:** Use a reasonable value.

**Fix:** Clamp to `min(args.jobs, os.cpu_count() or 8)` or a hard cap like 16.

---

### PID recycling in stale frontend override check

**File:** `site/site_config.py` — `is_stale_override()`

Uses `os.kill(pid, 0)` to check if the process that created the frontend
override `.mk` file is still alive. If the PID has been recycled by the OS for
a different process, the override is incorrectly considered non-stale. The
frontend config injection persists after the supervisor is gone.

**Trigger:** Long-lived systems where PIDs wrap around or systems with high
process churn.

**Workaround:** Delete the stale `.mk` file manually:
`rm /omd/sites/<site>/etc/check_mk/multisite.d/wato/cmk-dev-deploy-*.mk`

**Fix:** Write a process start time alongside the PID and verify both match
(Linux: check `/proc/<pid>/stat` field 22).

---

### Arbitrary TARGETED_THRESHOLD causes inconsistent deploy speed

**File:** `deployers/wheel_deployer.py` — `TARGETED_THRESHOLD = 15`

Below 15 changed files: fast targeted copy. At 16: full `rmtree` + `copytree`
of the entire package. The threshold is arbitrary and there is no indication
when it triggers. Deploy times vary during refactors.

**Trigger:** Changing 16+ files in a single Python package.

**Workaround:** None needed — correctness is fine, just slower than expected.

**Fix:** Either remove the threshold (always do targeted copy) or log when the
full-copy path is triggered so the developer understands the slowdown.

---

### Deleted files silently not tracked on git errors

**File:** `state/change_detector.py` — `_git_diff_deleted()`

Returns `[]` on any non-zero git exit code. A corrupt git index silently drops
all deletion tracking. Files that should be removed from the site persist.

**Trigger:** Running cmk-dev-deploy after a `git reset --hard` that leaves a
corrupt index, or on a repo with index lock issues.

**Workaround:** Run `git status` first to verify the index is healthy. If
things look wrong, `git fsck` and retry.

**Fix:** Treat `_git_diff_deleted` failures as a warning (not silent) and log
which files could not be checked.

---

### `GIT_QUICK = 5s` timeout too tight for cold caches

**File:** `core/timeouts.py` (`GIT_QUICK = 5`)

`git diff --name-only` against a large repo on a cold filesystem cache can
exceed 5 seconds. Deploy aborts with `ChangeDetectionError`. Works on second
try once the cache is warm.

**Trigger:** First deploy after a reboot or on NFS-mounted repos.

**Workaround:** Run again (cache will be warm).

**Fix:** Bump to 15 seconds, or make it configurable via env var.

---

### `BAZEL_BUILD = 600s` timeout too short for cold C++ builds

**File:** `core/timeouts.py` (`BAZEL_BUILD = 600`)

A cold C++ build from scratch can exceed 10 minutes. The timeout fires, deploy
aborts mid-way, and the site is left in a partially-deployed state.

**Trigger:** First deploy with C++ changes after `bazel clean` or on a new
machine.

**Workaround:** Run `bazel build //...` separately first, then deploy.

**Fix:** Bump to 1800s (30 min), or disable the timeout when stdout is a TTY
(interactive user can Ctrl-C).

---

### All packages report version 1.0.0

**File:** `deployers/wheel_deployer.py` — `_DIST_INFO_VERSION = "1.0.0"`

All deployed packages get hardcoded version `1.0.0` in their dist-info.
`pip show` and `importlib.metadata.version()` always return `1.0.0`, making it
impossible to distinguish which version of a package is deployed.

**Trigger:** Running `pip show cmk-*` on a site with deployed packages.

**Workaround:** Check the deploy state file or git log instead of pip.

**Fix:** Use the git commit short hash or timestamp as the version (e.g.,
`0.0.0+dev.a1b2c3d`).
