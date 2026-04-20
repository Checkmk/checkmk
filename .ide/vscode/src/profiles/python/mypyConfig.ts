/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { execFile, execSync } from 'child_process'
import * as fs from 'fs'
import * as path from 'path'
import * as vscode from 'vscode'

import { error, notifyInfo } from '../../core/log'
import { versionAtLeast } from '../../core/version'

const PACKAGE_BASE_DIRS = ['packages', 'non-free/packages']

const TOP_LEVEL_TEST_TREES = [
  'tests/unit',
  'tests/integration',
  'tests/composition',
  'tests/gui_e2e',
  'tests/gui_crawl',
  'tests/code_quality',
  'tests/agent-plugin-unit',
  'tests/agent_plugin_integration',
  'tests/agent-integration',
  'tests/extension_compatibility',
  'tests/integration_redfish',
  'tests/packaging'
]

// agents/plugins is Python 3.4+ compatible — strict mypy (configured for
// Python 3.13) will surface modern-syntax findings here. We include it
// because the strict checks reflect the project's intent.
const SPECIAL_TARGETS = ['omd/packages/omd/omdlib', 'agents/plugins', 'scripts']

interface MypyConfig {
  mypy_path?: string
  follow_imports?: string
  enable_error_code?: string[]
  overrides?: MypyOverride[]
  [key: string]: unknown
}

interface MypyOverride {
  module?: string[]
  [key: string]: unknown
}

function getMypyVersion(wsPath: string): Promise<string | null> {
  return new Promise((resolve) => {
    const bin = path.join(wsPath, '.venv', 'bin', 'mypy')
    execFile(bin, ['--version'], { encoding: 'utf8', timeout: 5000 }, (err, stdout) => {
      if (err) return resolve(null)
      const match = stdout.match(/mypy\s+(\d+\.\d+(?:\.\d+)?)/)
      resolve(match ? match[1] : null)
    })
  })
}

const VERSION_GATED_OPTIONS: Record<string, string> = {
  strict_bytes: '1.20',
  strict_equality_for_none: '1.20'
}

const VERSION_GATED_ERROR_CODES: Record<string, string> = {
  deprecated: '1.20',
  'exhaustive-match': '1.20'
}

function discoverPackageRoots(wsPath: string): string[] {
  const roots: string[] = []
  for (const baseDir of PACKAGE_BASE_DIRS) {
    const fullBase = path.join(wsPath, baseDir)
    if (!fs.existsSync(fullBase)) continue
    for (const name of fs.readdirSync(fullBase).sort()) {
      const pkgDir = path.join(fullBase, name)
      const hasCmk = fs.existsSync(path.join(pkgDir, 'cmk'))
      const hasPyproject = fs.existsSync(path.join(pkgDir, 'pyproject.toml'))
      if (hasCmk && hasPyproject) {
        roots.push(`${baseDir}/${name}`)
      }
    }
  }
  return roots
}

export function discoverMypyTargets(wsPath: string): string[] {
  const targets: string[] = []
  const tryAdd = (rel: string): void => {
    if (fs.existsSync(path.join(wsPath, rel))) {
      targets.push(rel)
    }
  }

  tryAdd('cmk')

  for (const baseDir of PACKAGE_BASE_DIRS) {
    const fullBase = path.join(wsPath, baseDir)
    if (!fs.existsSync(fullBase)) continue
    for (const name of fs.readdirSync(fullBase).sort()) {
      const pkgDir = path.join(fullBase, name)
      if (!fs.existsSync(path.join(pkgDir, 'pyproject.toml'))) continue
      const cmkRel = `${baseDir}/${name}/cmk`
      if (fs.existsSync(path.join(wsPath, cmkRel))) targets.push(cmkRel)
      const testsRel = `${baseDir}/${name}/tests`
      const testsAbs = path.join(wsPath, testsRel)
      // Skip per-package tests dirs that contain __init__.py: they all resolve
      // to a top-level module named "tests", and a single mypy daemon can't
      // distinguish them ("Duplicate module named 'tests'"). Bazel still
      // covers them via per-target mypy invocations. Namespace-package tests
      // (no __init__.py) coexist fine.
      if (fs.existsSync(testsAbs) && !fs.existsSync(path.join(testsAbs, '__init__.py'))) {
        targets.push(testsRel)
      }
    }
  }

  for (const tree of TOP_LEVEL_TEST_TREES) tryAdd(tree)
  for (const tree of SPECIAL_TARGETS) tryAdd(tree)

  return targets
}

type TargetsFilter = (catalog: string[]) => string[]
let targetsFilter: TargetsFilter | null = null

/**
 * Install a filter used by `applyDynamicMypyTargets()` to reduce the full
 * catalog to a subset before writing it to `mypy.targets`. Used by the
 * dynamic-targets module to start with a minimal set and expand on demand.
 * Pass null to clear.
 */
export function setMypyTargetsFilter(filter: TargetsFilter | null): void {
  targetsFilter = filter
}

export async function applyDynamicMypyTargets(wsPath: string, subset?: string[]): Promise<void> {
  const full = discoverMypyTargets(wsPath)
  const targets = subset ?? (targetsFilter ? targetsFilter(full) : full)
  const wsFolder = vscode.workspace.workspaceFolders?.[0]?.uri
  await vscode.workspace
    .getConfiguration('mypy', wsFolder)
    .update('targets', targets, vscode.ConfigurationTarget.WorkspaceFolder)
}

/**
 * Map a workspace-relative file path to the catalog target that covers it.
 * Longest-prefix match so nested targets (e.g. `packages/cmk-ccc/cmk` vs
 * `packages/cmk-ccc/tests`) resolve correctly. Returns null if no target
 * covers the file.
 */
export function resolveTargetForFile(relPath: string, catalog: string[]): string | null {
  let match: string | null = null
  for (const target of catalog) {
    if (relPath === target || relPath.startsWith(`${target}/`)) {
      if (!match || target.length > match.length) match = target
    }
  }
  return match
}

const PY_WALK_SKIP_DIRS = new Set([
  '__pycache__',
  '.venv',
  'node_modules',
  '.git',
  'bazel-bin',
  'bazel-out',
  'bazel-testlogs'
])

function walkPyFiles(wsPath: string, rel: string, out: string[]): void {
  const full = path.join(wsPath, rel)
  let entries: fs.Dirent[]
  try {
    entries = fs.readdirSync(full, { withFileTypes: true })
  } catch {
    return
  }
  for (const entry of entries) {
    if (PY_WALK_SKIP_DIRS.has(entry.name)) continue
    if (entry.name.startsWith('.') && entry.name !== '__init__.py') continue
    const sub = rel ? `${rel}/${entry.name}` : entry.name
    if (entry.isDirectory()) {
      walkPyFiles(wsPath, sub, out)
    } else if (entry.isFile() && entry.name.endsWith('.py')) {
      out.push(sub)
    }
  }
}

function computeModuleName(wsPath: string, fileRel: string, sortedRoots: string[]): string | null {
  for (const root of sortedRoots) {
    const prefix = `${root}/`
    if (fileRel.startsWith(prefix)) {
      let stripped = fileRel.substring(prefix.length)
      if (stripped.endsWith('/__init__.py')) {
        stripped = stripped.substring(0, stripped.length - '/__init__.py'.length)
      } else {
        stripped = stripped.substring(0, stripped.length - '.py'.length)
      }
      return stripped.replace(/\//g, '.') || null
    }
  }
  // No mypy_path base matched: fall back to __init__.py chain
  const parts: string[] = []
  let current: string
  if (fileRel.endsWith('/__init__.py')) {
    current = fileRel.substring(0, fileRel.length - '/__init__.py'.length)
    if (!current) return null
  } else {
    parts.push(path.basename(fileRel).slice(0, -3))
    current = path.dirname(fileRel)
  }
  while (current && current !== '.') {
    if (!fs.existsSync(path.join(wsPath, current, '__init__.py'))) break
    parts.unshift(path.basename(current))
    const parent = path.dirname(current)
    if (parent === current) break
    current = parent
  }
  return parts.join('.') || null
}

function detectModuleCollisions(
  wsPath: string,
  targets: string[],
  mypyPathRoots: string[]
): string[] {
  const sortedRoots = [...mypyPathRoots].sort((a, b) => b.length - a.length)
  const filesByModule = new Map<string, string[]>()
  const seen = new Set<string>()
  for (const target of targets) {
    const files: string[] = []
    walkPyFiles(wsPath, target, files)
    for (const file of files) {
      if (seen.has(file)) continue
      seen.add(file)
      const mod = computeModuleName(wsPath, file, sortedRoots)
      if (!mod) continue
      if (!filesByModule.has(mod)) filesByModule.set(mod, [])
      filesByModule.get(mod)!.push(file)
    }
  }
  const excludes: string[] = []
  for (const [, files] of filesByModule) {
    if (files.length < 2) continue
    files.sort()
    for (let i = 1; i < files.length; i++) excludes.push(files[i])
  }
  return excludes.sort()
}

function buildExcludeRegex(paths: string[]): string {
  if (paths.length === 0) return ''
  const escaped = paths.map((p) => p.replace(/[.+?^${}()|[\]\\]/g, '\\$&'))
  return `(^|/)(${escaped.join('|')})$`
}

function parsePyprojectToml(wsPath: string): Promise<MypyConfig | null> {
  const bin = path.join(wsPath, '.venv', 'bin', 'python')
  const script = `import tomllib,json,sys;data=tomllib.load(open('pyproject.toml','rb'));json.dump(data.get('tool',{}).get('mypy',{}),sys.stdout)`
  return new Promise((resolve) => {
    execFile(
      bin,
      ['-c', script],
      { encoding: 'utf8', cwd: wsPath, timeout: 5000 },
      (err, stdout) => {
        if (err) return resolve(null)
        try {
          resolve(JSON.parse(stdout))
        } catch {
          resolve(null)
        }
      }
    )
  })
}

export function buildMypyIniContent(
  version: string,
  config: MypyConfig,
  wsPath?: string,
  excludeRegex?: string
): string {
  const lines: string[] = [
    `# AUTO-GENERATED by CMK Dev Tools for VS Code`,
    `# Source: pyproject.toml [tool.mypy]`,
    `# Mypy version: ${version}`,
    `# Generated: ${new Date().toISOString()}`,
    `#`,
    `# Options unsupported by mypy ${version} have been removed.`,
    `# Re-generate via: CMK ▸ Cmd: Refresh Build Status (or change pyproject.toml)`,
    ``,
    `[mypy]`
  ]

  const skipKeys = ['overrides', 'enable_error_code']

  for (const [key, value] of Object.entries(config)) {
    if (skipKeys.includes(key)) continue

    const minVersion = VERSION_GATED_OPTIONS[key]
    if (minVersion && !versionAtLeast(version, minVersion)) {
      lines.push(`# ${key} = ${value}  # requires mypy >= ${minVersion}, you have ${version}`)
      continue
    }

    if (key === 'mypy_path' && typeof value === 'string') {
      const cleaned = value
        .replace(/\$MYPY_CONFIG_FILE_DIR\//g, '')
        .split(':')
        .map((p) => p.trim())
        .filter(Boolean)
      if (wsPath) {
        cleaned.push(...discoverPackageRoots(wsPath))
      }
      lines.push(`mypy_path = ${cleaned.join(':')}`)
      continue
    }

    if (key === 'follow_imports') {
      lines.push(`follow_imports = normal`)
      continue
    }

    if (typeof value === 'boolean') {
      lines.push(`${key} = ${value ? 'true' : 'false'}`)
    } else if (typeof value === 'string') {
      lines.push(`${key} = ${value}`)
    } else if (Array.isArray(value)) {
      lines.push(`${key} = ${value.join(', ')}`)
    }
  }

  if (config.enable_error_code) {
    const supported: string[] = []
    const skipped: string[] = []
    for (const code of config.enable_error_code) {
      const minVersion = VERSION_GATED_ERROR_CODES[code]
      if (minVersion && !versionAtLeast(version, minVersion)) {
        skipped.push(`${code} (requires >= ${minVersion})`)
      } else {
        supported.push(code)
      }
    }
    if (supported.length > 0) {
      lines.push(`enable_error_code = ${supported.join(', ')}`)
    }
    for (const s of skipped) {
      lines.push(`# enable_error_code: ${s} — skipped`)
    }
  }

  if (excludeRegex) {
    lines.push(`exclude = ${excludeRegex}`)
  }

  if (config.overrides) {
    for (const override of config.overrides) {
      const modules = override.module || []
      for (const mod of modules) {
        lines.push('')
        lines.push(`[mypy-${mod}]`)
        for (const [key, value] of Object.entries(override)) {
          if (key === 'module') continue
          if (typeof value === 'boolean') {
            lines.push(`${key} = ${value ? 'true' : 'false'}`)
          } else {
            lines.push(`${key} = ${value}`)
          }
        }
      }
    }
  }

  lines.push('')
  return lines.join('\n')
}

export async function generateAndWriteMypyConfig(wsPath: string): Promise<boolean> {
  const version = await getMypyVersion(wsPath)
  if (!version) return false
  const config = await parsePyprojectToml(wsPath)
  if (!config) return false
  const targets = discoverMypyTargets(wsPath)
  const mypyPathRoots = (typeof config.mypy_path === 'string' ? config.mypy_path : '')
    .replace(/\$MYPY_CONFIG_FILE_DIR\//g, '')
    .split(':')
    .map((p) => p.trim())
    .filter(Boolean)
    .concat(discoverPackageRoots(wsPath))
  const collisions = detectModuleCollisions(wsPath, targets, mypyPathRoots)
  const excludeRegex = buildExcludeRegex(collisions)
  const content = buildMypyIniContent(version, config, wsPath, excludeRegex)
  const changed = writeMypyIniIfChanged(wsPath, content)
  if (changed) {
    killDmypyDaemons(wsPath, { killAll: true })
  }
  return changed
}

function writeMypyIniIfChanged(wsPath: string, content: string): boolean {
  const outputPath = path.join(wsPath, '.vscode', '.mypy.ini')
  const outputDir = path.dirname(outputPath)
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true })
  }

  const existing = fs.existsSync(outputPath) ? fs.readFileSync(outputPath, 'utf8') : ''
  const normalize = (s: string) => s.replace(/# Generated:.*\n/, '')
  if (normalize(existing) === normalize(content)) {
    return false
  }

  fs.writeFileSync(outputPath, content, 'utf8')
  return true
}

function killDmypyDaemons(wsPath: string, { killAll = false } = {}): void {
  try {
    let activePid: number | null = null
    if (!killAll) {
      const statusFile = path.join(wsPath, '.dmypy.json')
      try {
        const status = JSON.parse(fs.readFileSync(statusFile, 'utf8'))
        if (status.pid && isProcessAlive(status.pid)) {
          activePid = status.pid
        }
      } catch {
        return
      }
      if (!activePid) return
    }

    const output = execSync(`ps -eo pid,args | grep '[d]mypy' | grep -F "${wsPath}/"`, {
      encoding: 'utf8',
      timeout: 3000
    }).trim()

    if (!output) return

    let killed = 0
    for (const line of output.split('\n')) {
      const trimmed = line.trim()
      if (!trimmed) continue
      if (/dmypy\s+(run|check|status|stop|kill|restart|suggest)\b/.test(trimmed)) continue
      const pid = parseInt(trimmed.split(/\s+/)[0], 10)
      if (!pid || pid === activePid) continue
      try {
        process.kill(pid, 'SIGTERM')
        killed++
      } catch {
        // Process already gone
      }
    }

    if (killed > 0) {
      notifyInfo(`CMK: Killed ${killed} ${killAll ? '' : 'stale '}dmypy daemon(s)`)
    }
  } catch {
    // Non-critical
  }
}

function isProcessAlive(pid: number): boolean {
  try {
    process.kill(pid, 0)
    return true
  } catch {
    return false
  }
}

export function registerMypyConfigWatcher(): vscode.Disposable[] {
  const wsPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
  if (!wsPath) return []

  const disposables: vscode.Disposable[] = []

  const cleanupInterval = setInterval(() => killDmypyDaemons(wsPath), 5 * 60 * 1000)
  disposables.push({
    dispose: () => {
      clearInterval(cleanupInterval)
    }
  })

  generateAndWriteMypyConfig(wsPath).then((changed) => {
    if (changed) {
      notifyInfo('CMK: Regenerated .vscode/.mypy.ini from pyproject.toml')
    }
  })

  applyDynamicMypyTargets(wsPath).catch((err) =>
    error(`Failed to apply mypy.targets: ${(err as Error).message}`)
  )

  const watcher = vscode.workspace.createFileSystemWatcher(
    new vscode.RelativePattern(wsPath, 'pyproject.toml')
  )

  watcher.onDidChange(() => {
    generateAndWriteMypyConfig(wsPath).then((changed) => {
      if (changed) {
        notifyInfo('CMK: Regenerated .vscode/.mypy.ini from pyproject.toml')
      }
    })
  })

  disposables.push(watcher)

  const packageWatcher = vscode.workspace.createFileSystemWatcher(
    new vscode.RelativePattern(wsPath, '{packages,non-free/packages}/*/pyproject.toml')
  )
  const refreshOnPackageChange = (): void => {
    applyDynamicMypyTargets(wsPath).catch((err) =>
      error(`Failed to apply mypy.targets: ${(err as Error).message}`)
    )
    generateAndWriteMypyConfig(wsPath).then((changed) => {
      if (changed) {
        notifyInfo('CMK: Regenerated .vscode/.mypy.ini after package change')
      }
    })
  }
  packageWatcher.onDidCreate(refreshOnPackageChange)
  packageWatcher.onDidDelete(refreshOnPackageChange)
  disposables.push(packageWatcher)

  return disposables
}

export function killAllDmypyDaemons(): void {
  const wsPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
  if (!wsPath) return
  killDmypyDaemons(wsPath, { killAll: true })
}
