/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as fs from 'fs'
import * as path from 'path'
import * as vscode from 'vscode'

import { error, log, notifyError, notifyInfo, notifyWarn } from '../../core/log'
import { safeExecAsync } from '../../core/shell'
import { killAllDmypyDaemons } from './mypyConfig'

const SETTING_ALLOCATOR = 'cmk.mypy.allocator'
const DMYPY_SETTING = 'dmypyExecutable'
const RUN_USING_INTERPRETER_SETTING = 'runUsingActiveInterpreter'
const WRAPPER_FILENAME = 'dmypy-jemalloc.sh'
const DISMISS_KEY = 'cmk.mypy.allocator.recommendationDismissed'

export type AllocatorMode = 'default' | 'jemalloc'

export interface InstallCommand {
  label: string
  command: string
}

export interface AllocatorSnapshot {
  mode: AllocatorMode
  libraryAvailable: boolean
  recommendationDismissed: boolean
  wrapperExists: boolean
  dmypyExecutableMatches: boolean
  runUsingInterpreterOff: boolean
}

let extContextRef: vscode.ExtensionContext | null = null

// Platform-stable results — detected once, cached for the session. Results
// either include a hit (string / InstallCommand) or an explicit miss (null).
let _jemallocPath: string | null | undefined = undefined
let _jemallocPathInflight: Promise<void> | null = null
let _installCmd: InstallCommand | null | undefined = undefined
let _installCmdInflight: Promise<void> | null = null
let _onAllocatorRefresh: (() => void) | null = null

export function setAllocatorRefreshCallback(cb: () => void): void {
  _onAllocatorRefresh = cb
}

/** Async detection of libjemalloc — never blocks the event loop. */
export async function detectJemallocPathAsync(): Promise<string | null> {
  if (_jemallocPath !== undefined) return _jemallocPath
  if (_jemallocPathInflight) {
    await _jemallocPathInflight
    return _jemallocPath ?? null
  }
  _jemallocPathInflight = (async () => {
    try {
      _jemallocPath = await probeJemallocPath()
    } finally {
      _jemallocPathInflight = null
    }
  })()
  await _jemallocPathInflight
  return _jemallocPath ?? null
}

async function probeJemallocPath(): Promise<string | null> {
  if (process.platform === 'linux') {
    const line = await safeExecAsync("ldconfig -p | awk '/libjemalloc\\.so\\.2/ {print $NF; exit}'")
    return line && fs.existsSync(line) ? line : null
  }
  if (process.platform === 'darwin') {
    const prefix = await safeExecAsync('brew --prefix jemalloc')
    if (!prefix) return null
    const candidate = path.join(prefix, 'lib', 'libjemalloc.dylib')
    return fs.existsSync(candidate) ? candidate : null
  }
  return null
}

/** Sync getter for hot paths. Returns the cached value if known, otherwise
 *  null and schedules an async probe whose completion triggers a sidebar
 *  refresh. */
export function detectJemallocPath(): string | null {
  if (_jemallocPath !== undefined) return _jemallocPath
  if (!_jemallocPathInflight) {
    _jemallocPathInflight = (async () => {
      try {
        _jemallocPath = await probeJemallocPath()
        _onAllocatorRefresh?.()
      } catch (err) {
        error(`jemalloc probe failed: ${(err as Error).message}`)
      } finally {
        _jemallocPathInflight = null
      }
    })()
  }
  return null
}

/** Async resolution of the platform's install command for libjemalloc. */
export async function installCommandForPlatformAsync(): Promise<InstallCommand | null> {
  if (_installCmd !== undefined) return _installCmd
  if (_installCmdInflight) {
    await _installCmdInflight
    return _installCmd ?? null
  }
  _installCmdInflight = (async () => {
    try {
      _installCmd = await probeInstallCommand()
    } finally {
      _installCmdInflight = null
    }
  })()
  await _installCmdInflight
  return _installCmd ?? null
}

async function probeInstallCommand(): Promise<InstallCommand | null> {
  if (process.platform === 'linux') {
    const [apt, dnf, pacman] = await Promise.all([
      safeExecAsync('command -v apt-get'),
      safeExecAsync('command -v dnf'),
      safeExecAsync('command -v pacman')
    ])
    if (apt) return { label: 'apt', command: 'sudo apt install -y libjemalloc2' }
    if (dnf) return { label: 'dnf', command: 'sudo dnf install -y jemalloc' }
    if (pacman) return { label: 'pacman', command: 'sudo pacman -S --needed jemalloc' }
    return null
  }
  if (process.platform === 'darwin') return { label: 'brew', command: 'brew install jemalloc' }
  return null
}

/** Build the wrapper script body. Pure function — feed it the detected lib
 *  path and the real dmypy path and it returns the exact bash content.
 *  Emits a clear hint to stderr if dmypy is missing at run time so the user
 *  knows to rebuild the venv. */
export function buildWrapperScript(jemallocPath: string, dmypyPath: string): string {
  const preloadVar = process.platform === 'darwin' ? 'DYLD_INSERT_LIBRARIES' : 'LD_PRELOAD'
  const forceFlat = process.platform === 'darwin' ? 'export DYLD_FORCE_FLAT_NAMESPACE=1\n' : ''
  const quotedDmypy = shellQuote(dmypyPath)
  return (
    `#!/usr/bin/env bash\n` +
    `# Generated by the cmk-vscode extension (cmk.mypy.allocator=jemalloc).\n` +
    `# Safe to delete — will be rewritten on the next window reload.\n` +
    `DMYPY=${quotedDmypy}\n` +
    `if [ ! -x "$DMYPY" ]; then\n` +
    `  echo "cmk-vscode: dmypy not found at $DMYPY — run \\"CMK \\xe2\\x96\\xb8 Cmd: Build venv\\" (or 'bazel run //:create_venv'), then reload the window." >&2\n` +
    `  exit 127\n` +
    `fi\n` +
    `export ${preloadVar}="\${${preloadVar}:+$${preloadVar}:}${jemallocPath}"\n` +
    forceFlat +
    `export PYTHONMALLOC=malloc\n` +
    `exec "$DMYPY" "$@"\n`
  )
}

function shellQuote(p: string): string {
  return `"${p.replace(/"/g, '\\"')}"`
}

function wrapperPathFor(context: vscode.ExtensionContext): string {
  return path.join(context.globalStorageUri.fsPath, WRAPPER_FILENAME)
}

function defaultDmypyPath(wsFolder: vscode.WorkspaceFolder): string {
  return path.join(wsFolder.uri.fsPath, '.venv', 'bin', 'dmypy')
}

function readAllocatorMode(): AllocatorMode {
  const v = vscode.workspace.getConfiguration().get<string>(SETTING_ALLOCATOR, 'default')
  return v === 'jemalloc' ? 'jemalloc' : 'default'
}

function readCurrentDmypyExecutable(wsFolder: vscode.WorkspaceFolder): string | undefined {
  return vscode.workspace.getConfiguration('mypy', wsFolder).get<string>(DMYPY_SETTING)
}

async function updateDmypyExecutable(
  wsFolder: vscode.WorkspaceFolder,
  value: string | undefined
): Promise<void> {
  await vscode.workspace
    .getConfiguration('mypy', wsFolder)
    .update(DMYPY_SETTING, value, vscode.ConfigurationTarget.WorkspaceFolder)
}

async function updateRunUsingInterpreter(
  wsFolder: vscode.WorkspaceFolder,
  value: boolean | undefined
): Promise<void> {
  await vscode.workspace
    .getConfiguration('mypy', wsFolder)
    .update(RUN_USING_INTERPRETER_SETTING, value, vscode.ConfigurationTarget.WorkspaceFolder)
}

function openInstallTerminal(install: InstallCommand): void {
  const terminal = vscode.window.createTerminal({ name: 'CMK ▸ Install jemalloc' })
  terminal.show(true)
  terminal.sendText(install.command)
}

/** Show the one-shot "libjemalloc not found" notification, wired to open a
 *  terminal running the correct install command on Accept. We do not silently
 *  degrade — the setting stays armed so a reload after install activates it. */
async function notifyMissingLibrary(): Promise<void> {
  const install = await installCommandForPlatformAsync()
  if (!install) {
    await notifyWarn(
      'CMK ▸ Mypy: jemalloc not detected on this platform.',
      `cmk.mypy.allocator=jemalloc requires libjemalloc. Your platform (${process.platform}) has no supported install path in this extension — install manually, then reload the window.`
    )
    return
  }
  const INSTALL = `Install via ${install.label}`
  const choice = await notifyWarn(
    'CMK ▸ Mypy: libjemalloc not found.',
    `dmypy will keep using the default allocator until libjemalloc is installed. Run: ${install.command}`,
    INSTALL
  )
  if (choice === INSTALL) openInstallTerminal(install)
}

/** Handler for the `cmk.mypy.installJemalloc` command. Idempotent: if the
 *  library is already on the host we say so instead of re-running install. */
async function installJemallocCommand(): Promise<void> {
  if (await detectJemallocPathAsync()) {
    await notifyInfo('CMK ▸ Mypy: libjemalloc already installed.')
    return
  }
  const install = await installCommandForPlatformAsync()
  if (!install) {
    await notifyError(
      'CMK ▸ Mypy: No supported install path for this platform.',
      `Platform ${process.platform} has no built-in install command — install libjemalloc manually, then reload the window.`
    )
    return
  }
  openInstallTerminal(install)
}

function writeWrapper(wrapperPath: string, content: string): void {
  fs.mkdirSync(path.dirname(wrapperPath), { recursive: true })
  fs.writeFileSync(wrapperPath, content, { mode: 0o755 })
}

function deleteWrapperIfPresent(wrapperPath: string): void {
  try {
    fs.unlinkSync(wrapperPath)
  } catch (err) {
    const code = (err as NodeJS.ErrnoException).code
    if (code && code !== 'ENOENT') log(`jemalloc wrapper delete failed: ${code}`)
  }
}

/** Reconcile `mypy.dmypyExecutable` to match `cmk.mypy.allocator`. Idempotent.
 *  - `"jemalloc"` + probe hit → write wrapper, point dmypyExecutable at it.
 *  - `"jemalloc"` + probe miss → notify once, leave setting armed.
 *  - `"default"` → restore the bundled venv default, delete wrapper.
 *  The extension owns `mypy.dmypyExecutable`: it unconditionally overrides any
 *  pre-existing value (including a custom path or one carried over from before
 *  the extension was installed) so the venv-pinned dmypy is always used. */
export async function applyAllocatorSetting(
  context: vscode.ExtensionContext,
  wsFolder: vscode.WorkspaceFolder
): Promise<void> {
  const wrapperPath = wrapperPathFor(context)
  const mode = readAllocatorMode()
  const current = readCurrentDmypyExecutable(wsFolder)

  if (mode === 'default') {
    // Restore the bundled defaults instead of leaving the keys unset — matangover
    // falls back to `python -m mypy.dmypy` when `mypy.dmypyExecutable` is empty,
    // which breaks the venv-pinned setup.
    const target = defaultDmypyPath(wsFolder)
    const previousRun = vscode.workspace
      .getConfiguration('mypy', wsFolder)
      .get<boolean>(RUN_USING_INTERPRETER_SETTING)
    if (current !== target) await updateDmypyExecutable(wsFolder, target)
    if (previousRun !== true) await updateRunUsingInterpreter(wsFolder, true)
    log(
      `cmk.mypy.allocator=default — set mypy.dmypyExecutable=${target}, runUsingActiveInterpreter=true`
    )
    if (current === wrapperPath || previousRun === false) {
      await killAllDmypyDaemons()
    }
    deleteWrapperIfPresent(wrapperPath)
    return
  }

  const libPath = await detectJemallocPathAsync()
  if (!libPath) {
    log('cmk.mypy.allocator=jemalloc but libjemalloc not detected — notifying')
    await notifyMissingLibrary()
    return
  }

  try {
    writeWrapper(wrapperPath, buildWrapperScript(libPath, defaultDmypyPath(wsFolder)))
  } catch (err) {
    error(`Failed to write jemalloc wrapper: ${(err as Error).message}`)
    return
  }

  const dmypyChanged = current !== wrapperPath
  if (dmypyChanged) {
    await updateDmypyExecutable(wsFolder, wrapperPath)
    log(`cmk.mypy.allocator=jemalloc — mypy.dmypyExecutable → ${wrapperPath}`)
  } else {
    log(`cmk.mypy.allocator=jemalloc — refreshed wrapper (lib=${libPath})`)
  }

  // matangover respects `mypy.dmypyExecutable` only when runUsingActiveInterpreter is false;
  // force it so our wrapper is invoked instead of `python -m mypy.dmypy`.
  const runUsingInterpreterBefore = vscode.workspace
    .getConfiguration('mypy', wsFolder)
    .get<boolean>(RUN_USING_INTERPRETER_SETTING, true)
  const interpreterChanged = runUsingInterpreterBefore !== false
  await updateRunUsingInterpreter(wsFolder, false)

  if (dmypyChanged || interpreterChanged) await killAllDmypyDaemons()
}

/** Snapshot for the IDE Health sidebar — covers both the opt-in recommendation
 *  (mode=default) and the setting-check diagnostics (mode=jemalloc). */
export function getAllocatorSnapshot(): AllocatorSnapshot {
  const wsFolder = vscode.workspace.workspaceFolders?.[0]
  const wrapperPath = extContextRef ? wrapperPathFor(extContextRef) : null
  const wrapperExists = wrapperPath !== null && fs.existsSync(wrapperPath)
  const currentDmypy = wsFolder ? readCurrentDmypyExecutable(wsFolder) : undefined
  const runUsingInterpreter = wsFolder
    ? (vscode.workspace
        .getConfiguration('mypy', wsFolder)
        .get<boolean>(RUN_USING_INTERPRETER_SETTING, true) ?? true)
    : true
  const workspaceDismissed = extContextRef?.workspaceState.get<boolean>(DISMISS_KEY, false) ?? false
  const userDismissed = vscode.workspace
    .getConfiguration('cmk.cockpit.jemalloc')
    .get<boolean>('ignoreRecommendation', false)
  return {
    mode: readAllocatorMode(),
    libraryAvailable: detectJemallocPath() !== null,
    recommendationDismissed: workspaceDismissed || userDismissed,
    wrapperExists,
    dmypyExecutableMatches: wrapperPath !== null && currentDmypy === wrapperPath,
    runUsingInterpreterOff: runUsingInterpreter === false
  }
}

/** Re-run the reconciliation on demand. Exposed as `cmk.mypy.reapplyJemalloc`
 *  so the user can recover when activation-time writes failed (e.g., dirty
 *  .vscode/settings.json buffer blocking the API). */
export async function reapplyJemallocAllocator(): Promise<void> {
  const wsFolder = vscode.workspace.workspaceFolders?.[0]
  if (!extContextRef || !wsFolder) {
    await notifyError('CMK ▸ Mypy: extension context not ready — reload the window and retry.')
    return
  }
  try {
    await applyAllocatorSetting(extContextRef, wsFolder)
  } catch (err) {
    const msg = (err as Error).message
    await notifyError('CMK ▸ Mypy: re-apply failed.', msg)
    return
  }
  await notifyInfo('CMK ▸ Mypy: re-applied allocator settings.')
}

/** Persist the "don't recommend jemalloc again" choice at user scope so a
 *  single click suppresses the recommendation everywhere — both the cockpit
 *  item dismiss-X and the IDE Health status-row dismiss button now share this
 *  single source of truth. The legacy workspaceState DISMISS_KEY remains
 *  honoured on read for users who dismissed before this change. */
export async function dismissAllocatorRecommendation(): Promise<void> {
  await vscode.workspace
    .getConfiguration('cmk.cockpit.jemalloc')
    .update('ignoreRecommendation', true, vscode.ConfigurationTarget.Global)
}

/** Flip `cmk.mypy.allocator` to "jemalloc" at workspace scope. Invoked from
 *  the sidebar recommendation banner. */
export async function enableJemallocFromRecommendation(): Promise<void> {
  await vscode.workspace
    .getConfiguration()
    .update(SETTING_ALLOCATOR, 'jemalloc', vscode.ConfigurationTarget.Workspace)
}

/** Flip `cmk.mypy.allocator` back to "default" at workspace scope. Invoked
 *  from the sidebar status row. */
export async function disableJemallocFromStatus(): Promise<void> {
  await vscode.workspace
    .getConfiguration()
    .update(SETTING_ALLOCATOR, 'default', vscode.ConfigurationTarget.Workspace)
}

export function registerJemallocAllocator(context: vscode.ExtensionContext): vscode.Disposable[] {
  extContextRef = context
  const wsFolder = vscode.workspace.workspaceFolders?.[0]
  if (!wsFolder) return []

  applyAllocatorSetting(context, wsFolder).catch((err) =>
    error(`jemalloc allocator init failed: ${(err as Error).message}`)
  )

  const dmypyWatcher = vscode.workspace.createFileSystemWatcher(
    new vscode.RelativePattern(wsFolder, '.venv/bin/dmypy')
  )
  const onDmypyAppeared = async (): Promise<void> => {
    if (readAllocatorMode() !== 'jemalloc') return
    log('jemalloc: .venv/bin/dmypy (re)appeared — reapplying allocator and killing stale daemons')
    try {
      await applyAllocatorSetting(context, wsFolder)
      await killAllDmypyDaemons()
    } catch (err) {
      error(`jemalloc dmypy-watcher handler failed: ${(err as Error).message}`)
    }
  }

  const disposables: vscode.Disposable[] = [
    dmypyWatcher,
    dmypyWatcher.onDidCreate(() => void onDmypyAppeared()),
    dmypyWatcher.onDidChange(() => void onDmypyAppeared()),
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (!e.affectsConfiguration(SETTING_ALLOCATOR)) return
      applyAllocatorSetting(context, wsFolder).catch((err) =>
        error(`jemalloc allocator reconfigure failed: ${(err as Error).message}`)
      )
    }),
    vscode.commands.registerCommand('cmk.mypy.installJemalloc', () =>
      installJemallocCommand().catch((err) =>
        error(`installJemalloc command failed: ${(err as Error).message}`)
      )
    ),
    vscode.commands.registerCommand('cmk.mypy.enableJemalloc', () =>
      enableJemallocFromRecommendation().catch((err) =>
        error(`enableJemalloc command failed: ${(err as Error).message}`)
      )
    ),
    vscode.commands.registerCommand('cmk.cockpit.jemalloc.dismissRecommendation', async () => {
      await dismissAllocatorRecommendation()
      log(
        'cockpit: jemalloc recommendation dismissed (cmk.cockpit.jemalloc.ignoreRecommendation=true)'
      )
    }),
    vscode.commands.registerCommand('cmk.cockpit.jemalloc.restoreRecommendation', async () => {
      await vscode.workspace
        .getConfiguration('cmk.cockpit.jemalloc')
        .update('ignoreRecommendation', undefined, vscode.ConfigurationTarget.Global)
      // Clear the legacy workspaceState flag too so previously-dismissed
      // workspaces stay un-dismissed.
      if (extContextRef) await extContextRef.workspaceState.update(DISMISS_KEY, undefined)
      log('cockpit: jemalloc recommendation restored')
    }),
    vscode.commands.registerCommand('cmk.mypy.reapplyJemalloc', () =>
      reapplyJemallocAllocator().catch((err) =>
        error(`reapplyJemalloc command failed: ${(err as Error).message}`)
      )
    ),
    {
      dispose: () => {
        const wrapperPath = wrapperPathFor(context)
        const current = readCurrentDmypyExecutable(wsFolder)
        if (current === wrapperPath) {
          updateDmypyExecutable(wsFolder, undefined).then(undefined, (err) =>
            error(`jemalloc allocator teardown failed: ${(err as Error).message}`)
          )
          updateRunUsingInterpreter(wsFolder, undefined).then(undefined, (err) =>
            error(`jemalloc allocator teardown failed: ${(err as Error).message}`)
          )
        }
        deleteWrapperIfPresent(wrapperPath)
      }
    }
  ]

  return disposables
}
