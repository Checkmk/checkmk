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

/** Like safeExec but falls back to the user's interactive shell when the
 *  command isn't found on the extension host's minimal PATH. */
export function shellExec(cmd: string, options?: { timeout?: number; cwd?: string }): string {
  const direct = safeExec(cmd, options)
  if (direct) return direct
  const shell = process.env.SHELL || '/bin/bash'
  return safeExec(`${shell} -ic '${cmd.replace(/'/g, "'\\''")}'`, options)
}
