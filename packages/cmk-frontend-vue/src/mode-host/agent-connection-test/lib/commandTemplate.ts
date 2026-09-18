/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

/**
 * Rewrites the command templates of the agent slideout for display.
 *
 * The producing ends are `cmk/gui/agent_commands.py` and, for the commercial
 * editions, `cmk/gui/nonfree/pro/agent_commands.py`. The welcome slide-in
 * (`src/welcome/components/first-host/`) builds its commands in the frontend
 * and still substitutes `[AGENT_DOWNLOAD_OTT]` on its own.
 */

/** What a command is for. Decides which `{{SERVER}}` and which token applies. */
export type CommandScope = 'download' | 'registration'

/** A one-time token as produced by `GenerateToken`. */
export type TokenValue = string | null | Error

export interface HostMacros {
  hostName: string
  siteId: string
  /** `{{SERVER}}` for download commands: the site's base URL. */
  downloadServer: string
  /** `{{SERVER}}` for registration commands: `<host>:<agent-receiver-port>`. */
  registrationServer: string
}

const DOWNLOAD_TOKEN_MACRO = '[AGENT_DOWNLOAD_OTT]'

/**
 * The registration command asks for the `agent_registration` user by default;
 * a generated token replaces that flag rather than a placeholder.
 */
const REGISTRATION_USER_FLAG = '--user agent_registration'

export function substituteMacros(
  cmd: string | undefined,
  scope: CommandScope,
  macros: HostMacros
): string {
  if (!cmd) {
    return ''
  }
  const server = scope === 'registration' ? macros.registrationServer : macros.downloadServer
  return cmd
    .replace(/{{HOSTNAME}}/g, macros.hostName)
    .replace(/{{SITE}}/g, macros.siteId)
    .replace(/{{SERVER}}/g, server)
}

/** Whether the command cannot be run without a one-time token. */
export function requiresToken(cmd: string | undefined, scope: CommandScope): boolean {
  if (!cmd) {
    return false
  }
  return scope === 'registration'
    ? cmd.includes(REGISTRATION_USER_FLAG)
    : cmd.includes(DOWNLOAD_TOKEN_MACRO)
}

/**
 * Substitute the one-time token. An empty token counts as no token: replacing
 * the placeholder with nothing would turn a working command into a broken one.
 */
export function applyToken(
  cmd: string | undefined,
  scope: CommandScope,
  token: TokenValue
): string {
  if (!cmd) {
    return ''
  }
  if (!token || token instanceof Error) {
    return cmd
  }
  // Substitute every occurrence, like the macros above: a command with two
  // authorized downloads would otherwise keep the second placeholder.
  return scope === 'registration'
    ? cmd.replaceAll(REGISTRATION_USER_FLAG, `--ott 0:${token}`)
    : cmd.replaceAll(DOWNLOAD_TOKEN_MACRO, token)
}
