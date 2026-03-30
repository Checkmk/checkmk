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
