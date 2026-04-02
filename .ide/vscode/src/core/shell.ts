import { execSync } from 'child_process'

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
