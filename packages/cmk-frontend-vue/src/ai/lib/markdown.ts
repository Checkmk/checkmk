/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { Marked, type Token, type Tokens } from 'marked'

type State = 'ok' | 'warn' | 'crit' | 'unknown'

const BADGE_LABEL: Record<State, string> = {
  ok: 'OK',
  warn: 'WARN',
  crit: 'CRIT',
  unknown: 'UNKNOWN'
}

const STATE_PATTERN = /^(?:ok|warn|crit|unknown)$/

function asBadgeState(text: string): State | null {
  const stripped = text
    .trim()
    .replace(/^\*\*(.+)\*\*$/, '$1')
    .toLowerCase()
  return STATE_PATTERN.test(stripped) ? (stripped as State) : null
}

function badgeHtmlToken(state: State): Tokens.Tag {
  const text = `<span class="ai-markdown-content__badge ai-markdown-content__badge--${state}">${BADGE_LABEL[state]}</span>`
  return {
    type: 'html',
    raw: text,
    text,
    block: false,
    inLink: false,
    inRawBlock: false
  }
}

function walkTokens(token: Token): void {
  if (token.type !== 'table') {
    return
  }
  const table = token as Tokens.Table
  for (const row of table.rows) {
    for (const cell of row) {
      const state = asBadgeState(cell.text)
      if (state === null) {
        continue
      }
      cell.tokens = [badgeHtmlToken(state)]
    }
  }
}

export const markdown = new Marked({
  breaks: true,
  walkTokens
})
