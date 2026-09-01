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
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { CommandBlock } from './types'

/** What a command is for. Decides which `{{SERVER}}` and which token applies. */
export type CommandScope = 'download' | 'registration'

/** A one-time token as produced by `GenerateToken`. */
export type TokenValue = string | null | Error

/** Why a command can or cannot be shown. */
export type TokenState = 'not-required' | 'ready' | 'missing' | 'failed'

export interface RenderedCommand {
  text: string
  tokenState: TokenState
}

/** Whether the command can be shown as it stands. */
export function isResolved(state: TokenState): boolean {
  return state === 'ready' || state === 'not-required'
}

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

/**
 * A registration that is not done by `cmk-agent-ctl` (e.g. a Helm value) has no
 * user flag to replace, so it carries this placeholder instead.
 */
const REGISTRATION_TOKEN_MACRO = '[AGENT_REGISTRATION_OTT]'

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
    ? cmd.includes(REGISTRATION_USER_FLAG) || cmd.includes(REGISTRATION_TOKEN_MACRO)
    : cmd.includes(DOWNLOAD_TOKEN_MACRO)
}

/**
 * Whether a token can be substituted into a command. An empty token counts as
 * no token: replacing the placeholder with nothing would turn a working
 * command into a broken one.
 */
export function isTokenUsable(token: TokenValue): token is string {
  return !!token && !(token instanceof Error)
}

export function applyToken(
  cmd: string | undefined,
  scope: CommandScope,
  token: TokenValue
): RenderedCommand {
  if (!cmd) {
    return { text: '', tokenState: 'not-required' }
  }
  if (!requiresToken(cmd, scope)) {
    return { text: cmd, tokenState: 'not-required' }
  }
  if (!isTokenUsable(token)) {
    return { text: cmd, tokenState: token instanceof Error ? 'failed' : 'missing' }
  }
  // Substitute every occurrence, like the macros above: a command with two
  // authorized downloads would otherwise keep the second placeholder.
  const text =
    scope === 'registration'
      ? cmd
          .replaceAll(REGISTRATION_USER_FLAG, `--ott 0:${token}`)
          .replaceAll(REGISTRATION_TOKEN_MACRO, `0:${token}`)
      : cmd.replaceAll(DOWNLOAD_TOKEN_MACRO, token)
  return { text, tokenState: 'ready' }
}

export interface RenderedBlock {
  title?: TranslatedString
  warning?: TranslatedString
  text: string
}

export interface RenderedBlocks {
  blocks: RenderedBlock[]
  /**
   * The worst state among the commands. Not resolved means at least one still
   * carries an unsatisfied placeholder, so none of them is shown.
   */
  tokenState: TokenState
}

/** Resolve a set of command blocks for display. */
export function renderBlocks(
  blocks: CommandBlock[],
  scope: CommandScope,
  macros: HostMacros,
  token: TokenValue = null
): RenderedBlocks {
  const rendered = blocks.map((block) =>
    applyToken(substituteMacros(block.command, scope, macros), scope, token)
  )
  const states = rendered.map((command) => command.tokenState)
  return {
    blocks: blocks.map((block, index) => ({
      ...(block.title === undefined ? {} : { title: block.title }),
      ...(block.warning === undefined ? {} : { warning: block.warning }),
      text: rendered[index]!.text
    })),
    tokenState:
      states.find((state) => state === 'failed') ??
      states.find((state) => state === 'missing') ??
      states.find((state) => state === 'ready') ??
      'not-required'
  }
}

/** Whether any of these commands cannot be run without a one-time token. */
export function blocksNeedToken(blocks: CommandBlock[], scope: CommandScope): boolean {
  return blocks.some((block) => requiresToken(block.command, scope))
}
