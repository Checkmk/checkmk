# cmk-dev-deploy

Deploy local changes to a running OMD site in under 5 seconds.

`cmk-dev-deploy` detects what you changed, builds only what is needed, and deploys it to your local OMD site. It uses a Bazel-generated deploy manifest as the single source of truth for what goes where, and a writable per-site clone of the OMD version directory so that deployments never touch the original install and are fully reversible.

## Prerequisites

- A local OMD site -- install one with `cmk-dev-install` / `cmk-dev-install-site` (from the `cmk-dev-site` pipx package)
- `sudo` access (for the one-time installation of the per-site sudoers rule)
- Bazel (the project's build system)
- Python >= 3.14 (the tool itself is stdlib-only; if the system Python is
  older, the launcher automatically falls back to the repo venv -- create it
  with `make .venv`)

## Quick Start

The tool is launched directly from the checkout -- deliberately not via
`bazel run`, so starting a deploy never queues behind other Bazel commands:

```bash
# Auto-detect site and deploy changed files
./scripts/cmk-dev-deploy.py

# Pass flags directly
./scripts/cmk-dev-deploy.py --site v260
./scripts/cmk-dev-deploy.py --watch
./scripts/cmk-dev-deploy.py --frontend --watch
```

You'll likely want a shell function so `cdd` works from any directory
inside a checkout -- like `bazel run` did, it picks the checkout you are
standing in:

```bash
cdd() { "$(git rev-parse --show-toplevel)/scripts/cmk-dev-deploy.py" "$@"; }
```

(An alias with a hard-coded absolute path works too, but then always
deploys that one checkout.) The launcher itself deploys the checkout it
lives in, independent of your current working directory. Deploys always
build the site's edition: the tool pins `--cmk_edition=<site edition>` on
every bazel command it runs.

Then:

```bash
cdd                        # auto-detect site and deploy
cdd --site v260            # deploy to a specific site
cdd --watch                # watch for changes and auto-deploy
cdd --frontend --watch     # full-stack: iBazel HMR + auto-deploy
```

**Tip: use `-v` to see what the tool is doing.** Verbose mode shows detected site details, per-file change lists, Bazel target resolution, dependency expansion, diff base source, and a timing timeline at the end. Highly recommended when getting started or debugging unexpected behavior:

```bash
cdd -v
```

```
[info] Detected site:
  Site:    v260
  Root:    /omd/sites/v260
  Edition: pro (PRO)
  Version: 2.6.0-2026.03.27.pro
  Commit:  a1b2c3d4e5f6
[info] Clone active on /omd/sites/v260
  Diff base: last deploy (f6e5d4c3b2a1)
[info] Changes detected: 12 file(s)
  Base commit: f6e5d4c3b2a1
  Python: 10 file(s)
  Config/Scripts: 2 file(s)
  Fast path eligible (Python only)
  Python:
    cmk/gui/views/layout.py
    cmk/gui/wato/pages/hosts.py
    ...
  Config/Scripts:
    agents/check_mk_agent.linux
    agents/plugins/mk_docker.py

  Deploying (2 step(s), max 4 worker(s))...
  config       deployed  0.3s  (2 spec(s))
  wheels       deployed  2.8s  (44 wheel(s) reinstalled)

[info] Services restarted: 2 in 1.0s

  Timeline (4.3s):
  config     ███░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  0.0-0.3s (7%)
  wheels     ███████████████████████████░░░░░░░░░░░░░  0.0-2.8s (65%)
  services   ░░░░░░░░░░░░░░░░░░░░░░░░░░░██████████████  2.8-4.3s (35%)

[ok] Deploy complete in 4.3s
```

On first run, the tool will:

1. Show the per-site sudoers rule and ask for one-time permission to install it
2. Clone the site's version directory to `/omd/dev-versions/<site>/<ver>`
3. Repoint the site's `version` symlink at the clone and restart the site

After the initial setup, subsequent deploys without `-v` show a compact summary:

```
[info] Site: v260 (pro)
[info] Clone active on /omd/sites/v260
  12 file(s) changed (10 python, 2 config)
  Build path: fast

  config       deployed  0.3s  (2 spec(s))
  wheels       deployed  2.8s  (44 wheel(s) reinstalled)

[info] Services restarted: 2 in 1.0s
[ok] Deploy complete in 4.3s
```

## Site Preparation: the Version Clone

Every deployment lands in a **writable per-site clone of the OMD version
directory** -- the original install under `/omd/versions/` is never
touched. The site's own `version` symlink (owned by the site user)
selects the clone:

```
/omd/sites/<site>/version -> /omd/dev-versions/<site>/<ver>   (clone, deploy-user owned)
                          -> ../../versions/<ver>             (pristine, after --purge)
```

The clone keeps the same directory basename as the original version, so
`omd` management tooling (which derives the version from the symlink
basename and reconstructs `/omd/versions/<ver>/...` paths) keeps operating
against the pristine install, while the site runtime follows the symlink
into the clone.

**Privilege model.** One mechanism, no SSH, no fallback chain: a per-site
sudoers drop-in (`<user> ALL=(<site>) NOPASSWD: ALL`). Every run probes for
it non-interactively; if missing, the tool shows the exact rule and asks for
one-time permission to install it (`visudo -cf` validated). `--print-setup`
emits the manual commands for an admin instead; `--remove-setup` deletes the
drop-in. After bootstrap, no deploy, restart, reboot, `--full`, or `--purge`
ever needs sudo again. Declining the rule still deploys: the run then asks
for your sudo password directly (cached for the sudo timestamp duration, so
service restarts late in a long watch session may fail), and the consent
prompt returns on the next run.

| Event              | What happens                                                                      |
| ------------------ | --------------------------------------------------------------------------------- |
| First deploy       | one consented sudo bootstrap per site, clone version dir, swap symlink, restart   |
| Subsequent deploys | write into the clone directly (plain file ops)                                    |
| Reboot             | nothing to do — the symlink persists, the site starts with the **deployed** code  |
| `--full`           | delete + recreate clone, swap, restart (no sudo)                                  |
| `--purge`          | revert symlink to the pristine version, delete clone (no sudo); site left stopped |
| `omd update`       | stale clone discarded on the next deploy, incremental state reset (full deploy)   |

**`--purge` reverts code only.** Site configuration (`etc/`) and runtime
state (`var/`) are real directories that deploys never touch, so purging
cannot eat WATO changes or runtime state.

A leftover OverlayFS mount from an older cmk-dev-deploy version is detected
and refused with manual recovery instructions (`umount` plus removal of
`/var/tmp/cmk-dev-deploy/<site>`).

## A Dedicated Bazel Server

Bazel executes one command at a time per output base. On the checkout's
default server, every deploy would queue behind whatever `bazel test` or
`bazel build` you have running -- and block it in return. The tool
therefore runs all of its Bazel commands (`build`, `run //:deploy-python`,
`query`, `cquery`, `info`) against a dedicated output base:

```
~/.cache/cmk-dev-deploy/bazel/<hash of the checkout path>
```

Deploys and your own Bazel commands run in parallel. What the second
server costs, and why it is cheap:

- **Disk:** a second output base (several GB once warm). The repo-wide
  shared disk cache (`--disk_cache` in `.bazelrc`) makes actions built by
  either server cache hits for the other, so the duplication costs disk,
  not build time.
- **RAM:** a second server JVM, bounded to 3 GB.
- **First deploy:** pays one-time cold analysis and cache-served rebuilds;
  afterwards the server stays warm. Because the deploy server only ever
  sees the site edition's configuration, its analysis cache is never
  discarded by configuration flips.

The deploy server never touches the checkout's `bazel-bin`/`bazel-out`
convenience symlinks: building commands run with `--symlink_prefix=/`
(create no symlinks), and artifacts are located via `bazel info` and
`bazel cquery` instead.

Opt out with `--shared-bazel-server` (or `CDD_SHARED_BAZEL_SERVER=1`) to
use the checkout's default server, e.g. when disk space is tight.
`CDD_BAZEL_OUTPUT_BASE` overrides the output base location. To reclaim
the disk space:

```bash
bazel --output_base=<path> clean --expunge    # or simply: rm -rf <path>
```

## Modes of Operation

### One-Shot Deploy (default)

Detect changes, deploy, and exit.

```bash
cdd
```

Computes the diff between your working tree and the last deployed commit, categorizes changes (Python, C++, Rust, config, etc.), and runs only the deployers that have work to do. Python changes are deployed by reinstalling the edition's wheels via `bazel run //:deploy-python`; Bazel's action cache keeps unchanged wheels free.

```bash
cdd --full              # force full deploy (deletes and recreates the clone)
cdd --dry-run           # show what would be deployed without executing
cdd --commit feature-branch  # use a specific ref for change detection (implies --full)
```

### Watch Mode

Continuously monitor for changes and auto-deploy.

```bash
cdd --watch
```

Polls the git working tree every 1 second using content-aware hashing (not just file lists). When a change is detected, waits 0.3s for rapid saves to settle (debounce), then runs a deploy cycle. Prints a one-line summary after each cycle.

```
[info] Watching for changes on site v260... (Ctrl-C to stop)

--- watch cycle 1 ---
  wheels       deployed  2.8s  (44 wheel(s) reinstalled)
  Cycle 1: deployed wheels in 3.0s

--- watch cycle 2 ---
  wheels       deployed  2.6s  (44 wheel(s) reinstalled)
  config       deployed  0.2s  (1 spec(s))
  Cycle 2: deployed wheels, config in 2.9s
```

Press Ctrl-C to stop.

### Frontend Mode

Deploy backend first, then start the iBazel frontend supervisor for hot module replacement.

```bash
cdd --frontend
```

Runs a one-shot deploy of all backend changes, then starts `ibazel run //packages/cmk-frontend-vue:vite` as a foreground subprocess. iBazel watches the frontend source tree and triggers Vite rebuilds automatically, providing hot module replacement for Vue/TypeScript files. The tool also writes a site config override (`load_frontend_vue = "inject"`) so the GUI loads frontend assets from the Vite dev server. Press Ctrl-C to stop; the override is removed on shutdown.

iBazel is auto-downloaded (v0.28.0) on first use and cached at `~/.cache/cmk-dev-deploy/`.

When `--frontend` is active, the `packages/cmk-frontend-vue` Bazel target is filtered out of regular deploy builds to avoid conflicts with iBazel.

### Combined Mode

The recommended mode for full-stack development: iBazel HMR for frontend, auto-deploy for backend.

```bash
cdd --frontend --watch
```

Starts the iBazel frontend supervisor after the initial deploy, then enters the watch loop. Backend changes trigger re-deploys while iBazel stays alive and continues to serve frontend changes via HMR.

The supervisor is health-checked before each poll cycle and after each deploy cycle. If iBazel crashes, the watch loop stops and prints the last stderr output for diagnostics. If a deploy fails in combined mode, the frontend supervisor is stopped automatically.

## Site Resolution

The tool resolves which OMD site to deploy to in this priority order:

1. **`--site NAME`** -- explicit CLI argument
2. **`.site` file** -- a file at the repo root containing the site name (one name per line, `#` comments supported)
3. **`SITE` env var** -- deprecated fallback, prints a warning
4. **`omd sites --bare`** -- auto-selects if exactly one site exists; errors if multiple sites found

To persist your site choice without typing `--site` every time:

```bash
echo 'v260' > .site
```

## CLI Reference

### Deploy Flags

| Flag                    | Short | Default     | Description                                                                                                                                                                                                       |
| ----------------------- | ----- | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--site NAME`           | `-s`  | auto-detect | Target OMD site name                                                                                                                                                                                              |
| `--info`                |       |             | Show site info and exit without deploying                                                                                                                                                                         |
| `--full`                |       |             | Force full deploy: delete and recreate the clone, deploy everything                                                                                                                                               |
| `--dry-run`             | `-n`  |             | Show deploy plan without executing                                                                                                                                                                                |
| `--watch`               | `-w`  |             | Watch for changes and auto-deploy                                                                                                                                                                                 |
| `--frontend`            |       |             | Start iBazel frontend supervisor after deploying                                                                                                                                                                  |
| `--commit REF`          |       |             | Use a specific commit/branch/tag for change detection instead of the working tree (implies `--full`). Manifest and builds still use the current working tree — check out the ref first to deploy its exact state. |
| `--verbose`             | `-v`  | 0           | Increase verbosity (`-v` for detailed output)                                                                                                                                                                     |
| `--jobs N`              | `-j`  | 4           | Max parallel deployment workers                                                                                                                                                                                   |
| `--no-restart`          |       |             | Deploy files only, skip service restarts                                                                                                                                                                          |
| `--rebuild-manifest`    |       |             | Force manifest regeneration before deploying                                                                                                                                                                      |
| `--shared-bazel-server` |       |             | Run bazel commands on the checkout's default server instead of the tool's dedicated one (deploys then queue behind other bazel commands)                                                                          |
| `--purge`               |       |             | Revert site to original state and remove deploy data, then exit (no deploy)                                                                                                                                       |
| `--print-setup`         |       |             | Print the admin commands that set up the clone backend, then exit                                                                                                                                                 |
| `--remove-setup`        |       |             | Remove the clone backend's sudoers rule, then exit                                                                                                                                                                |
| `--json-errors`         |       |             | On error, output a JSON diagnostic bundle to stdout (for automation)                                                                                                                                              |

### Flag Combinations

Some flags cannot be combined:

- `--watch` cannot be used with `--dry-run` or `--info`
- `--frontend` cannot be used with `--dry-run` or `--info`
- `--commit` cannot be used with `--watch` or `--info`
- `--full` cannot be used with `--info`
- `--purge` cannot be used with any other mode flag
- `--print-setup` / `--remove-setup` combine only with `--site`

## Deploy Pipeline

Each deploy cycle follows these stages:

1. **Site resolution** -- Auto-detect the OMD site (see [Site Resolution](#site-resolution)), read its edition and build commit.

2. **Site preparation** -- Ensure the site runs on its writable version clone. On first run this clones the version directory (30-60s, nearly free with reflink).

3. **Manifest check** -- Verify the deploy manifest is up-to-date. The manifest is a JSON file auto-generated from Bazel targets that maps source paths to site destinations. If stale, it is regenerated automatically (or forced with `--rebuild-manifest`).

4. **Change detection** -- Run `git diff` against the last deployed commit (from saved state) or the site build commit. Categorize files into Python, C++, Rust, Vue, config, data, build, test, and other.

5. **Deployer selection** -- Three parallel deployers, each running only if its source paths have changes:
   - **Config deployer** -- copies config/data files (agents, notifications, locale, etc.) using `shutil.copy2` or locale compilation (`msgfmt`)
   - **Bazel builder** -- builds C++, Rust, and frontend Bazel targets, then installs artifacts to the site with correct permissions and post-install fixups (e.g. `setcap` for ICMP binaries)
   - **Wheel deployer** -- runs `bazel run //:deploy-python`, which builds the edition's `py_wheel` targets and force-reinstalls them against the site Python via uv (including bytecode compilation)

6. **Parallel execution** -- Run applicable deployers in parallel (up to `--jobs` workers).

7. **Service restart** -- Only restart services affected by the deployers that actually ran. Uses a three-tier resolution: explicit service specs > wheel convention (any wheel triggers `apache:reload`) > config spec annotations. Services are restarted in dependency order.

8. **State save** -- Record the current HEAD commit and per-deployer dirty file hashes for incremental tracking. Partial failures save state only for successful deployers.

## Incremental Deploy

State tracking enables incremental deploys: only changes since the last successful deploy are processed.

- **State file:** Stored under the OMD site's tmp directory. Contains per-deployer records with the last deployed git commit and dirty file hashes.
- **Per-deployer tracking:** Each deployer (config, bazel, wheels) maintains its own commit pointer. A deployer only runs if files within its source paths have changed since its last successful run.
- **Dirty file detection:** Files that are modified in the working tree but not yet committed are tracked by content hash. If you edit a file, deploy, then edit it again, only the second change triggers a new deploy. Files reverted to their committed state are detected and redeployed with the clean version.
- **Branch switch detection:** When the current branch differs from the recorded branch, state is cleared and a full deploy runs automatically.
- **Reset:** Use `--full` to clear state and force a complete redeployment (also recreates the clone). The `--commit REF` flag implies `--full`.

## Edition Filtering

The codebase supports five editions: `community`, `pro`, `ultimate`, `ultimatemt`, and `cloud`. The tool reads the target site's edition from its version symlink and:

- Skips Bazel install specs that don't match the site edition (e.g. CMC binaries on a community site)
- Builds edition-correct wheels (`--cmk_edition` resolves the wheel lists and the `select()`ed non-free contents of `//cmk:whl`)
- Skips edition-gated service restarts (e.g. CMC and DCD only on pro+ editions)

## Troubleshooting

On any error, the tool automatically captures a diagnostic bundle at `~/.cache/cmk-dev-deploy/diagnostics/crash-<timestamp>.json` (respects `$XDG_CACHE_HOME`). This includes environment info, Bazel state, manifest state, deploy state, and log tail. Share this file when reporting issues.

Use `--json-errors` to also print the bundle to stdout (useful for CI/automation).

## Scope Boundaries

**What cmk-dev-deploy IS:**

- A development tool for deploying local changes to a running OMD site
- Bazel-native: reads a deploy manifest generated from BUILD files for compiled assets and install specs
- Covers Python packages (wheel deployment), config/data files, Bazel-compiled artifacts (C++, Rust, frontend bundles)
- Edition-aware: filters out code for editions not matching the target site
- Reversible: all changes land in a per-site version clone that can be purged

**What cmk-dev-deploy is NOT:**

- Not a production deployment tool -- it is for local development only
- Not a replacement for `bazel build` -- it uses Bazel for compiled assets and reads the Bazel-generated manifest
- Not a CI/CD pipeline -- it deploys to a single local OMD site, not to remote hosts or containers

---

<details>
<summary><strong>Internals: Manifest and Deploy Specs</strong></summary>

### Deploy Manifest

The deploy manifest is a JSON file that maps Bazel targets to site destinations. It is auto-generated by querying Bazel for the wheels deployed by `//:deploy-python` (wheel prefixes), `deps_packages` packaging targets (config specs), and install targets (compiled artifact specs). The manifest is cached and regenerated when stale or when `--rebuild-manifest` is passed.

It contains:

- **Wheel prefixes** -- the source-tree prefixes covered by wheel deployment, used for step gating, `.py` categorization, coverage warnings, and the service-restart convention. Which wheels get deployed (per edition) is defined in `bazel/rules/deploy.bzl`, not here.
- **Config specs** -- Config/data directories deployed via `copy_dir`, `install_files`, or `locale_compile` methods. Each spec maps a source prefix to a site destination.
- **Install specs** -- Compiled artifacts (C++ binaries, Rust binaries, frontend dist bundles) built by Bazel and installed with specific permissions and post-install actions.

### deploy_specs.toml

The file `cmk/dev_deploy/manifest/deploy_specs.toml` contains:

- **Package specs** -- compiled artifact deploy definitions that have no Bazel representation (binary name, install destination, post-install actions like `setcap`)
- **Service overrides** -- non-default service restart mappings keyed by Bazel target. Convention: all `py_wheel` targets automatically trigger `apache:reload`; only non-default restarts need explicit entries.
- **Config overrides** -- extra metadata for auto-discovered config specs (includes patterns, `delete_extra`, `file_chmod`, services).

### Deployer state machine

Each deployer maintains independent state:

- `git_commit` -- last deployed commit
- `dirty_file_hashes` -- MD5 hashes of uncommitted file contents at deploy time
- `deployed_at` -- timestamp of last deployment

The global `diff_base_commit` advances to HEAD after every cycle, independent of per-deployer commits. This prevents stale deployers (repeatedly skipped because their source paths are untouched) from drifting and causing unnecessary rebuilds.

</details>
