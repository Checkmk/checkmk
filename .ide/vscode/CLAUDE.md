# CMK VS Code Extension — AI Agent Instructions

## Quick Reference

- **Language**: TypeScript, bundled via esbuild into a single CommonJS file
- **Entry point**: `src/extension.ts` → compiled to `out/extension.js`
- **UI**: Sidebar sections are webviews rendered by per-section modules in `src/sidebar/`
- **Config-driven**: JSON files in `config/` define commands, extensions, settings, snippets, templates
- **Config loading**: Workspace-first (`<workspace>/.ide/vscode/config/`), falls back to bundled VSIX copy
- **Dependencies**: `typescript`, `esbuild` (dev only); zero runtime npm dependencies

## Build & Install

After **every** code change, rebuild and reinstall the VSIX:

1. **Build the VSIX** via Bazel, then **install** into the active VS Code profile.
   The profile must be passed via `--profile` so the extension is installed into the correct
   profile (not the default one). Resolve it from VS Code's `storage.json`:

```sh
# Build the VSIX via Bazel
bazel build //.ide/vscode:vsix

# Resolve the VS Code profile for this workspace
PROFILE=$(python3 -c "
import json, os
storage = os.path.expanduser('~/.config/Code/User/globalStorage/storage.json')
with open(storage) as f: d = json.load(f)
ws = 'file://' + os.path.realpath('.')
assoc = d.get('profileAssociations', {}).get('workspaces', {})
pid = assoc.get(ws, '__default__profile__')
if pid == '__default__profile__':
    print('Default')
else:
    profiles = {p['location']: p['name'] for p in d.get('userDataProfiles', [])}
    print(profiles.get(pid, 'Default'))
")

# Install into the resolved profile
code --profile "$PROFILE" --install-extension bazel-bin/.ide/vscode/cmk-vscode.vsix --force
```

The user must reload VS Code (`Ctrl+Shift+P` → "Developer: Reload Window") to pick up changes.
Always run both steps together. Never skip the install step.

## Architecture

### Build Toolchain

- **TypeScript** (`tsconfig.json`): Target ES2022, strict mode, CommonJS output to `out/`
- **esbuild** (`esbuild.js`): Bundles `src/extension.ts` → `out/extension.js`, CSS imported as text via `loader: { '.css': 'text' }`, `vscode` marked external
- **Bazel** (`BUILD`): genrule runs `npm ci` → `node esbuild.js` → `npx @vscode/vsce package`
- **CSS type declarations**: `src/css.d.ts` allows `import css from './style.css'` as string

### Entry Point (`src/extension.ts`)

`activate(context)` registers:

1. **Always-on**: status bar logo, dashboard, build status bar, templates, build commands, IDE pickers, Gerrit push, OMD, cmk-dev-site (create site + update check)
2. **Family-gated**: Python, Frontend, Rust — each wrapped in `profileManager.register()` with disable-settings
3. **Version check**: Compares installed vs workspace version, prompts "Rebuild & Install" on mismatch
4. **First-run wizard**: Detects missing workspace settings and offers to open the dashboard
5. **Profile detector**: Monitors file activity and suggests enabling/disabling profiles

### Config Loading (`src/core/config.ts`)

`loadConfig(name)` uses a two-tier lookup:

1. **Workspace config** (branch-aware): `<workspace>/.ide/vscode/config/<name>.json`
2. **Bundled fallback**: `<installed-extension>/config/<name>.json`

This means switching branches updates configs without rebuilding the VSIX.

### Sidebar (`src/sidebar.ts` + `src/sidebar/`)

The sidebar has one activity bar container (`cmk-dashboard`) with multiple webview sections.
Each section is a `SectionViewProvider` instance registered via `vscode.window.registerWebviewViewProvider()`.

**Sections** (defined in `SECTIONS` array): `environment`, `omd`, `ideHealth`, `profiles`

Each section lives in its own folder under `src/sidebar/` with an `index.ts` (render + message handling + data helpers) and a `style.css`. Shared utilities live in `src/sidebar/html.ts` (esc, getNonce, wrap, renderLoading) and `src/sidebar/base.css`.

**Rendering flow**:

1. `refreshStateCache()` in `sidebar.ts` gathers all data into `_stateCache`
2. Each section's `render(state, codiconUri, cspSource)` returns full HTML
3. `wrap(nonce, css, body, codiconUri)` in `html.ts` assembles the HTML document with CSP, base styles, and codicon font
4. Section-specific CSS is imported as text strings at build time (esbuild `.css` loader)

**Message handling**: Each section exports `handleMessage(msg, ctx)` returning `true` if handled. The orchestrator delegates to each section in sequence.

**State cache** is shared across all sections and refreshed on:

- Section becoming visible
- Manual refresh (refresh icon per section)
- Post-action refresh (after build commands, profile toggles, OMD actions)
- 30-second auto-refresh (OMD)

### Modules (`src/`)

| File                                  | Purpose                                                                  |
| ------------------------------------- | ------------------------------------------------------------------------ |
| `sidebar.ts`                          | Sidebar orchestrator: state cache, section providers, message dispatch   |
| `sidebar/html.ts`                     | Shared HTML utilities: esc, getNonce, wrap, renderLoading                |
| `sidebar/base.css`                    | Shared CSS (cards, buttons, badges, env rows, ext-family)                |
| `sidebar/types.ts`                    | Shared sidebar type definitions                                          |
| `sidebar/issues.ts`                   | IssuesProvider tree + activity bar badge                                 |
| `sidebar/environment/`                | Environment section (render, messages, data helpers, CSS)                |
| `sidebar/profiles/`                   | Profiles section (render, messages, CSS)                                 |
| `sidebar/ideHealth/`                  | IDE Health section (render, messages, data helpers, CSS)                 |
| `sidebar/omd/`                        | OMD Sites section (render, messages, CSS)                                |
| `core/config.ts`                      | JSON config loading (workspace-first), variable resolution, shell escape |
| `core/constants.ts`                   | Display names for families (`FAMILY_DISPLAY`) and profile labels         |
| `core/shell.ts`                       | `safeExec()` wrapper around `execSync`, returns empty string on failure  |
| `core/tasks.ts`                       | Shell task execution helpers (`runCommand`, `waitForTask`)               |
| `core/log.ts`                         | Logging and error handling utilities                                     |
| `core/version.ts`                     | Semver parsing, `versionNewer()`, `versionAtLeast()` comparisons         |
| `core/versionCheck.ts`                | Version mismatch detection + "Rebuild & Install" prompt                  |
| `profiles/profileManager.ts`          | Language profile lifecycle (Py/UI/Rs)                                    |
| `profiles/profileDetector.ts`         | Auto-suggest profiles from file activity                                 |
| `profiles/python/mypyConfig.ts`       | Auto-generate `.mypy.ini` from `pyproject.toml`                          |
| `profiles/python/interpreter.ts`      | Python interpreter resolution                                            |
| `profiles/python/snippets.ts`         | Code snippet registration                                                |
| `profiles/python/bazelTest.ts`        | Bazel-based Python test runner                                           |
| `profiles/frontend/prettierConfig.ts` | Auto-generate `.prettier.config.cjs`                                     |
| `build/buildStatus.ts`                | Build target staleness detection, status bar                             |
| `build/settings.ts`                   | Settings mismatch detection, apply logic, context keys                   |
| `omd/omd.ts`                          | OMD site discovery, status, auth, service commands, site creation        |
| `omd/devSiteTools.ts`                 | cmk-dev-site install/update detection, PyPI update check                 |
| `omd/proxy.ts`                        | Unix socket → TCP proxy via socat (livestatus, Redis, etc.)              |
| `setup/idePicker.ts`                  | Multi-select QuickPick for IDE setup families                            |
| `setup/templates.ts`                  | File template creation                                                   |
| `gerrit.ts`                           | Gerrit push integration                                                  |
| `whatsNew.ts`                         | "What's New" markdown preview on version upgrade (reads `changelog/v*.md`) |

### Configuration (`config/`)

| File               | Purpose                                                          |
| ------------------ | ---------------------------------------------------------------- |
| `commands.json`    | Build commands (name, shell cmd, required profile, post-actions) |
| `extensions.json`  | Extension families (IDs, required flag, disable-settings)        |
| `settings.json`    | Expected settings per family at folder/workspace/user scope      |
| `snippets.json`    | Code snippets                                                    |
| `templates.json`   | File templates with placeholder substitution                     |
| `checkmk.dict.txt` | cSpell dictionary                                                |

## UI Conventions

### Icons

Use **VS Code codicons** exclusively. Never use emoji or Unicode symbol entities for icon buttons.

The codicon font (`icons/codicon.ttf`) is loaded in webviews via `@font-face` in `wrap()` (`src/sidebar/html.ts`).
The `codiconUri` is resolved per-provider using `webview.asWebviewUri()` and passed through
each section's `render()` → `wrap()`. Only sections that use codicons need to pass it to `wrap()`.

Usage in HTML:

```html
<span class="codicon codicon-terminal"></span>
```

Available codicon classes (add more in `wrap()` as needed):

- `codicon-terminal` — console/terminal
- `codicon-link-external` — open in browser
- `codicon-trash` — delete
- `codicon-copy` — copy to clipboard
- `codicon-refresh` — rebuild/refresh
- `codicon-chevron-right` — accordion chevron (rotates 90° when open)
- `codicon-wrench` — apply/fix single setting
- `codicon-play` — start (OMD site)
- `codicon-stop-circle` — stop (OMD site)

Browse all icons: https://microsoft.github.io/vscode-codicons/dist/codicon.html
To add a new icon, find its character code in `icons/codicon.ttf` or the codicon CSS, then add a
`.codicon-<name>::before { content: "\\xxxx"; }` rule in the `codiconCss` block inside `wrap()` in `src/sidebar/html.ts`.

### Icon Buttons

Icon buttons use the `.btn-icon` class. They are:

- **Icon only** — no text label, use `title` attribute for tooltip
- **Transparent background** — only shows background on hover
- Contain a single `<span class="codicon codicon-xxx"></span>`

```html
<button class="btn btn-small btn-icon" data-action="my-action" title="My tooltip">
  <span class="codicon codicon-terminal"></span>
</button>
```

For destructive actions, add `.btn-danger` which turns the hover background red.

### Accordion Sections

Collapsible sections (extensions, OMD sites) use the pattern:

- Container: `.ext-family` or `.omd-site` — toggled via `.open` class
- Header: `data-action="toggle-accordion"` — click handler toggles `.open` on closest container
- Chevron: `.ext-chevron.codicon.codicon-chevron-right` rotates 90° when open
- Body: hidden via `max-height: 0`, revealed via `max-height: Npx` when `.open`

### Adding a New Sidebar Section

1. Create `src/sidebar/mySection/index.ts` exporting `render(state, codiconUri, cspSource)` and `handleMessage(msg, ctx)`
2. Create `src/sidebar/mySection/style.css` with section-specific styles
3. Import the section module in `sidebar.ts` and add to `sectionModules` and `SECTIONS`
4. Add view in `package.json` under `views.cmk-dashboard`
5. Add refresh command in `package.json` (`cmk.dashboard.refresh.mySection`)
6. Add menu entry in `package.json` under `menus.view/title`
7. If it needs data, add to `refreshStateCache()` in `sidebar.ts`

### Adding a New Webview Action

1. Add `data-action="my-action"` and any `data-*` attributes to the HTML element
2. Add `case 'my-action':` in the client-side click handler (inside `wrap()` in `src/sidebar/html.ts`)
3. Post a message: `vscode.postMessage({ type: 'myAction', ... })`
4. Add `case 'myAction':` in the section's `handleMessage()` in `src/sidebar/<section>/index.ts`

### Adding a New Command

1. Register in `package.json` under `commands` and optionally `commandPalette` with `when` clause
2. Register handler via `vscode.commands.registerCommand()` in the relevant module
3. Push to `context.subscriptions`

## OMD Integration (`src/omd/omd.ts`)

OMD commands require `sudo`. Due to `tty_tickets`, sudo credentials cached in a terminal
are not visible to Node.js `execSync`. The workaround:

1. **Auth command** (`cmk.omdAuth`): Opens a terminal running `sudo -v`, then dumps
   `omd status --bare <site>` output to temp files in `/tmp/cmk-omd-status/`
2. **Sudo keepalive**: After successful auth, a background interval runs `sudo -n -v`
   every 4 minutes for up to 1 hour, also refreshing the status files.
3. **`getOmdStatus()`**: Reads cached status files (valid for 10 min), falls back to
   `sudo -n` (non-interactive, 1s timeout to avoid blocking).
4. **Service actions** (start/stop/restart): Run via `tasks.ts` `runCommand()` in a
   visible terminal. Each action appends a status dump so the cache is updated immediately.
5. **Force refresh**: The OMD section refresh button calls `forceRefreshOmdStatusFiles()`,
   which tries `sudo -n` first, then falls back to a terminal task if `tty_tickets` blocks it.

Site discovery reads `/omd/sites/` directory + `site.conf` files — no sudo needed.

### OMD Site Header Buttons

Each site header shows conditional icon buttons:

- **Play/Stop** — starts or stops the site (hidden when status is unknown/needs auth)
- **Terminal** — opens a `sudo omd su <site>` console
- **Browser** — opens `http://localhost:<port>/<site>/` (only if port is configured)
- **Trash** — deletes the site (with confirmation modal)

### OMD Socket Proxy (`src/omd/proxy.ts`)

Exposes OMD Unix sockets as TCP ports on localhost via `socat`. This allows external
tools to connect to site services (livestatus, Redis, mkeventd, rrdcached) without sudo.

**Known sockets** are defined in `KNOWN_SOCKETS` with default TCP ports in `DEFAULT_PORTS`.
The `cmk.omdProxy` command opens a QuickPick to select site + service, then spawns a
background `socat` process. Active proxies are tracked in the `activeProxies` field of
`StateCache` and displayed in the OMD sidebar section.

Proxy processes are cleaned up on extension deactivation via `registerProxyCleanup()`.

### cmk-dev-site Integration (`src/omd/devSiteTools.ts`)

- **Create Site** (`cmk.omdCreateSite`): Available when `cmk-dev-site` is on PATH. The `+` button in the OMD section title bar triggers site creation.
- **Update check**: On activation, checks PyPI for a newer `cmk-dev-site` version (once per 24h). Prompts to upgrade via `pipx upgrade cmk-dev-site`.
- **Context key**: `cmk.devSiteInstalled` controls visibility of the create-site button.

## Documentation

- **Keep `README.md` in sync** with the current state of the extension. When adding or removing features, update the README accordingly.
- Keep the README clean — no AI-specific notes, no implementation details. It is user-facing.
- Put AI-relevant architecture notes and conventions in this `CLAUDE.md` file.
- Do not add inline JSDoc or code comments unless the logic is genuinely non-obvious.

### Confluence sync

The file `.ide/vscode/ci_parity.md` (VSCode & Bazel: Local vs CI Parity) is mirrored to Confluence at:

- **Space**: DEV (Developer Documentation > IDE > VSCode)
- **Page ID**: 190555122
- **URL**: <https://wiki.lan.checkmk.net/pages/viewpage.action?pageId=190555122>

When `.ide/vscode/ci_parity.md` changes, update the Confluence page by running:

```sh
CONFLUENCE_TOKEN=<token> python .ide/vscode/scripts/update_confluence_vscode_page.py
```

Use `--dry-run` to preview the generated XHTML without making API calls.

## Settings Dashboard

The settings section groups mismatched settings by plugin family in collapsible accordion sections
(reusing the `.ext-family` accordion pattern). Each family group contains:

- **Apply {Family}** button — applies all mismatches for that family (`applyFamilyMismatches` message, filtered by `family` display name)
- **Wrench icon** — applies a single setting via `writeMismatchSetting()`
- **Copy icon** — copies the full JSON key+value to clipboard (e.g. `{"key": value}`)
- **Apply All** button at the top — applies all displayed mismatches across all families at once

Settings are written using section-scoped `getConfiguration(section).update(leaf, ...)` with
`ConfigurationTarget.Workspace` to handle settings owned by inactive extensions. A fallback
to full-key `getConfiguration(undefined, wsFolder)` handles edge cases.

### Loading States

Async webview actions (OMD start/stop, settings apply, profile toggle) show a per-button
loading spinner: the clicked button is disabled and its icon replaced with a spinning ↻.
The spinner is applied client-side in the `<script>` block of `wrap()` for actions listed
in the `ASYNC_ACTIONS` set. When the host calls `refreshAll()`, the section HTML is replaced,
clearing the spinner. `showSectionLoading()` is reserved for destructive or full-section ops.

## Key Patterns

- **`safeExec(cmd, opts)`** (`core/shell.ts`): `execSync` wrapper that returns empty string on failure
- **`runCommand(name, cmd)`**: Creates a VS Code `ShellExecution` task shown in the terminal panel
- **`waitForTask(exec)`**: Returns a promise that resolves with the exit code when the task finishes
- **`refreshAll()`**: Refreshes state cache + all section providers. Exported from `sidebar.ts` and passed to `registerOmd()` as callback.
- **Context keys**: Set via `vscode.commands.executeCommand('setContext', key, value)` to control `when` clauses in `package.json`
- **CSP**: Webviews use nonce-based Content-Security-Policy. All inline styles and scripts must carry the nonce. External resources require explicit CSP directives (e.g. `font-src` for codicons). CSS is imported as text at build time and injected into the `<style>` tag with nonce.

## Commits

Bump the patch version in `package.json` with every commit.

After bumping the version (and after each `git commit --amend` that changes the
version-bump commit), run:

```sh
bazel run //.ide/vscode:generate_changelog
git add .ide/vscode/changelog/v<new-version>.md
git commit --amend --no-edit
```

This writes/refreshes `.ide/vscode/changelog/v<new-version>.md` from the commit
message. The `tests/changelog.test.ts` vitest enforces this — it fails if no
changelog file exists for the current `package.json` version. The bundled
changelog files drive the in-extension "What's New" markdown preview shown to
users on version upgrade (see `src/whatsNew.ts`).

Use conventional commit format with `(vscode)` scope. First line must be **≤ 50 chars**.
Second line is the new extension version. Third line is the Jira ticket ID.
Body follows after a blank line.

```text
<type>(vscode): <short summary>
v<extension-version>
<JIRA-TICKET-ID>

<optional detailed description>
```

**Types**: `feat`, `fix`, `refactor`, `style`, `test`, `docs`, `chore`, `perf`

Example:

```text
feat(vscode): add per-button spinner
v0.1.43
CMK-33200

Replace whole-section loading with per-button spinners
for async actions like OMD start/stop and settings apply.
```
