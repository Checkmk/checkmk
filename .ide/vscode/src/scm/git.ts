/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { execFile } from 'child_process'
import * as fs from 'fs'
import * as path from 'path'
import { promisify } from 'util'
import * as vscode from 'vscode'

const execFileAsync = promisify(execFile)

export function repoRoot(): string | undefined {
  return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
}

/** Resolve the real git directory for `cwd`, handling worktrees / submodules
 *  where `.git` is a file containing `gitdir: <path>`. */
function gitDir(cwd: string): string | null {
  try {
    const gitPath = path.join(cwd, '.git')
    const st = fs.statSync(gitPath)
    if (st.isDirectory()) return gitPath
    if (st.isFile()) {
      const content = fs.readFileSync(gitPath, 'utf8').trim()
      const m = content.match(/^gitdir:\s+(.+)$/)
      if (m) return path.isAbsolute(m[1]) ? m[1] : path.resolve(cwd, m[1])
    }
  } catch {
    // ignore
  }
  return null
}

/** Read the current branch from `.git/HEAD` directly — no subprocess, no
 *  event-loop stall on the activation path. Returns the branch name, the
 *  detached SHA (truncated to 12 chars), or '' when the directory is not a
 *  git workspace. */
export function currentBranch(cwd: string): string {
  const dir = gitDir(cwd)
  if (!dir) return ''
  try {
    const content = fs.readFileSync(path.join(dir, 'HEAD'), 'utf8').trim()
    if (content.startsWith('ref: refs/heads/')) return content.slice('ref: refs/heads/'.length)
    if (content.startsWith('ref: ')) return content.slice('ref: '.length)
    return content.slice(0, 12)
  } catch {
    return ''
  }
}

/** True for an internal Checkmk dev checkout, detected by a git remote pointing
 *  at the internal Gerrit review server. Community clones (github.com) push via
 *  pull requests instead, so the internal-workflow SCM UI (Gerrit push, custom
 *  branch checkout) is hidden there. Detected from the dedicated Gerrit SSH port
 *  (29418); the review host name is a secondary signal. Reads `.git/config`
 *  directly — a local file read, no subprocess on the activation path. */
export function isInternalCheckout(cwd: string): boolean {
  const dir = gitDir(cwd)
  if (!dir) return false
  try {
    const config = fs.readFileSync(path.join(dir, 'config'), 'utf8')
    return /:29418\b/.test(config) || /\breview\.[\w.-]+\b/.test(config)
  } catch {
    return false
  }
}

/** Run `git <args>` asynchronously without going through a shell.
 *  Returns trimmed stdout on success, or null on failure. */
export async function gitAsync(cwd: string, args: string[]): Promise<string | null> {
  try {
    const { stdout } = await execFileAsync('git', args, { cwd, maxBuffer: 16 * 1024 * 1024 })
    return stdout.trim()
  } catch {
    return null
  }
}
