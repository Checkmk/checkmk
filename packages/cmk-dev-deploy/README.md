# cmk-dev-deploy

Deploy local changes to a running OMD site in under 5 seconds.

`cmk-dev-deploy` detects what you changed, builds only what is needed, and deploys it to your local OMD site. It uses a Bazel-generated deploy manifest as the single source of truth for what goes where, and an OverlayFS layer on the site directory so that every deployment is reversible.

## Prerequisites

- A local OMD site -- install one with `cmk-dev-install` / `cmk-dev-install-site` (from the `cmk-dev-site` pipx package)
- `sudo` access (required for OverlayFS mount/unmount)
- Bazel (the project's build system)
- Optional: a dedicated SSH key for passwordless site-user commands (see [SSH key setup](#ssh-key-setup))

## Quick Start

The tool is invoked via Bazel:

```bash
# Auto-detect site and deploy changed files
bazel run //packages/cmk-dev-deploy:cmk-dev-deploy-bin

# Pass flags after --
bazel run //packages/cmk-dev-deploy:cmk-dev-deploy-bin -- --site v260
bazel run //packages/cmk-dev-deploy:cmk-dev-deploy-bin -- --watch
bazel run //packages/cmk-dev-deploy:cmk-dev-deploy-bin -- --frontend --watch
```

You'll likely want a shell alias:

```bash
alias cdd='bazel run //packages/cmk-dev-deploy:cmk-dev-deploy-bin --'
```

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
[info] Overlay active on /omd/sites/v260
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
  wheels       deployed  0.8s  (1 deployed, 3 skipped)

[info] Services restarted: 2 in 1.0s

  Timeline (2.3s):
  config     ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  0.0-0.3s (13%)
  wheels     ░░███████████████░░░░░░░░░░░░░░░░░░░░░░░░  0.3-1.1s (35%)
  services   ░░░░░░░░░░░░░░░░░████████████████████████  1.1-2.3s (52%)

[ok] Deploy complete in 2.3s
```

On first run, the tool will:

1. Ask for your sudo password (to mount the OverlayFS)
2. Stop the site, mount the overlay, restart the site
3. Inject an SSH key so subsequent service restarts don't need sudo

After the initial setup, subsequent deploys without `-v` show a compact summary:

```
[info] Site: v260 (pro)
[info] Overlay active on /omd/sites/v260
  12 file(s) changed (10 python, 2 config)
  Build path: fast

  config       deployed  0.3s  (2 spec(s))
  wheels       deployed  0.8s  (1 deployed, 3 skipped)

[info] Services restarted: 2 in 1.0s
[ok] Deploy complete in 2.3s
```

## OverlayFS

Every deployment goes through an OverlayFS mounted on the site directory. This means:

- **All changes are reversible.** The original site files are untouched in the lower layer; your deployments land in the upper layer. Run `--purge` to remove the overlay and revert the site to its original state.
- **Survives reboots.** The upper layer is stored in `/var/tmp/cmk-dev-deploy/<site>/` which persists across reboots. After a reboot the overlay mount is gone, but the next `cmk-dev-deploy` run re-mounts with the existing upper layer.
- **Symlink materialization.** OMD sites use top-level symlinks (`bin/`, `lib/`, `share/`) pointing to the shared version directory. Since OverlayFS only intercepts writes within its mount point, the tool "materializes" these symlinks on first mount by copying their targets into the upper layer. This happens once per OMD version and takes 30-60s.
- **Requires sudo.** The `mount` and `umount` operations need root. The tool prompts for your password once per session and caches the sudo timestamp.

### Overlay lifecycle

| Event              | What happens                                                                            |
| ------------------ | --------------------------------------------------------------------------------------- |
| First deploy       | sudo prompt, stop site, materialize symlinks, mount overlay, inject SSH key, start site |
| Subsequent deploys | Overlay already mounted, deploy directly                                                |
| Reboot             | Overlay mount gone, upper layer preserved on disk; next run re-mounts                   |
| `--full`           | Tear down overlay, recreate from scratch, then deploy                                   |
| `--purge`          | Tear down overlay, delete upper layer, site reverts to original state (stopped)         |

## Modes of Operation

### One-Shot Deploy (default)

Detect changes, deploy, and exit.

```bash
cdd
```

Computes the diff between your working tree and the last deployed commit, categorizes changes (Python, C++, Rust, config, etc.), and runs only the deployers that have work to do. For Python-only changes, uses a fast path (direct wheel copy) that skips Bazel entirely.

```bash
cdd --full              # force full deploy (tears down and recreates the overlay)
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
  wheels       deployed  0.5s  (targeted: 3 files)
  Cycle 1: deployed wheels in 0.7s

--- watch cycle 2 ---
  wheels       deployed  0.4s  (targeted: 1 files)
  config       deployed  0.2s  (1 spec(s))
  Cycle 2: deployed wheels, config in 0.8s
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

| Flag                 | Short | Default     | Description                                                                                                                                                                                                       |
| -------------------- | ----- | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--site NAME`        | `-s`  | auto-detect | Target OMD site name                                                                                                                                                                                              |
| `--info`             |       |             | Show site info and exit without deploying                                                                                                                                                                         |
| `--full`             |       |             | Force full deploy: tear down overlay, recreate, deploy everything                                                                                                                                                 |
| `--dry-run`          | `-n`  |             | Show deploy plan without executing                                                                                                                                                                                |
| `--watch`            | `-w`  |             | Watch for changes and auto-deploy                                                                                                                                                                                 |
| `--frontend`         |       |             | Start iBazel frontend supervisor after deploying                                                                                                                                                                  |
| `--commit REF`       |       |             | Use a specific commit/branch/tag for change detection instead of the working tree (implies `--full`). Manifest and builds still use the current working tree — check out the ref first to deploy its exact state. |
| `--verbose`          | `-v`  | 0           | Increase verbosity (`-v` for detailed output)                                                                                                                                                                     |
| `--jobs N`           | `-j`  | 4           | Max parallel deployment workers                                                                                                                                                                                   |
| `--no-restart`       |       |             | Deploy files only, skip service restarts                                                                                                                                                                          |
| `--rebuild-manifest` |       |             | Force manifest regeneration before deploying                                                                                                                                                                      |
| `--purge`            |       |             | Remove overlay and revert site to original state, then exit (no deploy)                                                                                                                                           |
| `--json-errors`      |       |             | On error, output a JSON diagnostic bundle to stdout (for automation)                                                                                                                                              |

### Flag Combinations

Some flags cannot be combined:

- `--watch` cannot be used with `--dry-run` or `--info`
- `--frontend` cannot be used with `--dry-run` or `--info`
- `--commit` cannot be used with `--watch` or `--info`
- `--full` cannot be used with `--info`
- `--purge` cannot be used with any other mode flag

## Deploy Pipeline

Each deploy cycle follows these stages:

1. **Site resolution** -- Auto-detect the OMD site (see [Site Resolution](#site-resolution)), read its edition and build commit.

2. **Overlay setup** -- Ensure the OverlayFS is mounted. On first run this includes symlink materialization and SSH key injection.

3. **Manifest check** -- Verify the deploy manifest is up-to-date. The manifest is a JSON file auto-generated from Bazel targets that maps source paths to site destinations. If stale, it is regenerated automatically (or forced with `--rebuild-manifest`).

4. **Change detection** -- Run `git diff` against the last deployed commit (from saved state) or the site build commit. Categorize files into Python, C++, Rust, Vue, config, data, build, test, and other.

5. **Dependency expansion** -- If changed files belong to packages with declared dependencies, expand to include downstream packages that may need rebuilding.

6. **Deployer selection** -- Three parallel deployers, each running only if its source paths have changes:
   - **Config deployer** -- copies config/data files (agents, notifications, locale, etc.) using `shutil.copy2` or locale compilation (`msgfmt`)
   - **Bazel builder** -- builds C++, Rust, and frontend Bazel targets, then installs artifacts to the site with correct permissions and post-install fixups (e.g. `setcap` for ICMP binaries)
   - **Wheel deployer** -- deploys Python packages as wheels (direct source copy for development packages, Bazel-built wheels for generated packages)

7. **Parallel execution** -- Run applicable deployers in parallel (up to `--jobs` workers).

8. **Service restart** -- Only restart services affected by the deployers that actually ran. Uses a three-tier resolution: explicit service specs > wheel convention (any wheel triggers `apache:reload`) > config spec annotations. Services are restarted in dependency order.

9. **State save** -- Record the current HEAD commit and per-deployer dirty file hashes for incremental tracking. Partial failures save state only for successful deployers.

## Incremental Deploy

State tracking enables incremental deploys: only changes since the last successful deploy are processed.

- **State file:** Stored under the OMD site's tmp directory. Contains per-deployer records with the last deployed git commit and dirty file hashes.
- **Per-deployer tracking:** Each deployer (config, bazel, wheels) maintains its own commit pointer. A deployer only runs if files within its source paths have changed since its last successful run.
- **Dirty file detection:** Files that are modified in the working tree but not yet committed are tracked by content hash. If you edit a file, deploy, then edit it again, only the second change triggers a new deploy. Files reverted to their committed state are detected and redeployed with the clean version.
- **Branch switch detection:** When the current branch differs from the recorded branch, state is cleared and a full deploy runs automatically.
- **Reset:** Use `--full` to clear state and force a complete redeployment (also recreates the overlay). The `--commit REF` flag implies `--full`.

## Edition Filtering

The codebase supports five editions: `community`, `pro`, `ultimate`, `ultimatemt`, and `cloud`. The tool reads the target site's edition from its version symlink and:

- Skips Bazel install specs that don't match the site edition (e.g. CMC binaries on a community site)
- Removes edition-specific directories (`nonfree/pro/`, `nonfree/cloud/`, etc.) after wheel deployment
- Skips edition-gated service restarts (e.g. CMC and DCD only on pro+ editions)

## SSH Key Setup

After the overlay is mounted, the tool injects your SSH public key into the site user's `authorized_keys` on the overlay. This lets subsequent `omd restart` commands run via SSH instead of sudo, which is faster and doesn't require a cached sudo timestamp.

The tool looks for keys in this order:

1. `~/.ssh/cmk-dev-deploy` (dedicated, passphrase-free -- recommended)
2. `~/.ssh/id_ed25519`
3. `~/.ssh/id_rsa`
4. `~/.ssh/id_ecdsa`

To create a dedicated deploy key (recommended, avoids Yubikey touch prompts):

```bash
ssh-keygen -t ed25519 -f ~/.ssh/cmk-dev-deploy -N ""
```

If SSH is unavailable, the tool falls back to `sudo --login -u <site>` for service commands.

## Troubleshooting

On any error, the tool automatically captures a diagnostic bundle at `~/.cache/cmk-dev-deploy/diagnostics/crash-<timestamp>.json` (respects `$XDG_CACHE_HOME`). This includes environment info, Bazel state, manifest state, deploy state, and log tail. Share this file when reporting issues.

Use `--json-errors` to also print the bundle to stdout (useful for CI/automation).

## Scope Boundaries

**What cmk-dev-deploy IS:**

- A development tool for deploying local changes to a running OMD site
- Bazel-native: reads a deploy manifest generated from BUILD files for compiled assets and install specs
- Covers Python packages (wheel deployment), config/data files, Bazel-compiled artifacts (C++, Rust, frontend bundles)
- Edition-aware: filters out code for editions not matching the target site
- Reversible: all changes land on an OverlayFS upper layer that can be purged

**What cmk-dev-deploy is NOT:**

- Not a production deployment tool -- it is for local development only
- Not a replacement for `bazel build` -- it uses Bazel for compiled assets and reads the Bazel-generated manifest
- Not a CI/CD pipeline -- it deploys to a single local OMD site, not to remote hosts or containers

---

<details>
<summary><strong>Internals: Manifest and Deploy Specs</strong></summary>

### Deploy Manifest

The deploy manifest is a JSON file that maps Bazel targets to site destinations. It is auto-generated by querying Bazel for `py_wheel` targets (wheel specs), `deps_packages` packaging targets (config specs), and install targets (compiled artifact specs). The manifest is cached and regenerated when stale or when `--rebuild-manifest` is passed.

Three types of deploy specs are derived from the manifest:

- **Wheel specs** -- Python packages deployed as wheels. `deploy_mode` is either `direct` (copy source files), `flat` (copy from flat layout), or `generated` (bazel build + extract from wheel zipfile).
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
