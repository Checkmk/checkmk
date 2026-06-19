import { exec, execSync } from 'child_process'
import { promisify } from 'util'

const execAsync = promisify(exec)

/** Async counterpart to safeExec. Returns trimmed stdout, or empty string on
 *  failure / timeout. Does not block the event loop. */
export async function safeExecAsync(
  cmd: string,
  options?: { timeout?: number; cwd?: string }
): Promise<string> {
  try {
    const { stdout } = await execAsync(cmd, {
      encoding: 'utf-8',
      timeout: options?.timeout ?? 5000,
      cwd: options?.cwd
    })
    return stdout.trim()
  } catch {
    return ''
  }
}

/** Run a shell command, returning trimmed stdout or empty string on failure. */
export function safeExec(cmd: string, options?: { timeout?: number; cwd?: string }): string {
  try {
    return execSync(cmd, {
      encoding: 'utf-8',
      timeout: options?.timeout ?? 5000,
      cwd: options?.cwd
    }).trim()
  } catch {
    return ''
  }
}

/** Wrap a command so it runs through the user's interactive login shell, which
 *  sources their shell profile (e.g. ~/.zshrc, ~/.bashrc). Use this for dev
 *  tools that live on a profile-managed PATH (git aliases like `git workon`,
 *  pyenv shims, ~/bin scripts) and are therefore invisible to the extension
 *  host's minimal PATH. */
export function interactiveShellCommand(cmd: string): string {
  const shell = process.env.SHELL || '/bin/bash'
  return `${shell} -ic '${cmd.replace(/'/g, "'\\''")}'`
}

/** Like safeExec but falls back to the user's interactive shell when the
 *  command isn't found on the extension host's minimal PATH. */
export function shellExec(cmd: string, options?: { timeout?: number; cwd?: string }): string {
  const direct = safeExec(cmd, options)
  if (direct) return direct
  return safeExec(interactiveShellCommand(cmd), options)
}

/** Async counterpart to shellExec. Tries the direct command first, falls back
 *  to the user's interactive shell on miss. Does not block the event loop. */
export async function shellExecAsync(
  cmd: string,
  options?: { timeout?: number; cwd?: string }
): Promise<string> {
  const direct = await safeExecAsync(cmd, options)
  if (direct) return direct
  return safeExecAsync(interactiveShellCommand(cmd), options)
}
