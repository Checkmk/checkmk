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

const SERVICE_CONTEXT_LIST_PATTERN = /(<h1[^>]*>\s*Service context\s*<\/h1>\s*)<ul>/i
const RECOMMENDED_ACTIONS_LIST_PATTERN = /(<h1[^>]*>\s*Recommended actions\s*<\/h1>\s*)<ol>/i

function tagSpecialLists(html: string): string {
  return html
    .replace(SERVICE_CONTEXT_LIST_PATTERN, '$1<ul class="ai-markdown-content__service-context">')
    .replace(
      RECOMMENDED_ACTIONS_LIST_PATTERN,
      '$1<ol class="ai-markdown-content__recommended-actions">'
    )
}

export type QualityLevel = 'high' | 'medium' | 'low'

const QUALITY_LABELS = 'Confidence|Data Quality'
const QUALITY_LEVELS = 'High|Medium|Low'

const QUALITY_LINE_RE = new RegExp(
  `^[ \\t]*(?:${QUALITY_LABELS}):[ \\t]*\\*\\*(${QUALITY_LEVELS})\\*\\*[ \\t]*$`,
  'im'
)

export function extractQualityLevel(text: string): QualityLevel | null {
  const level = QUALITY_LINE_RE.exec(text)?.[1]?.toLowerCase()
  return level === 'high' || level === 'medium' || level === 'low' ? level : null
}

export function stripQualityLineFromText(text: string): string {
  return text.replace(QUALITY_LINE_RE, '')
}

const markdown = new Marked({
  breaks: true,
  walkTokens,
  hooks: {
    postprocess: tagSpecialLists
  }
})

export async function parseMarkdown(text: string): Promise<string> {
  return markdown.parse(text)
}
