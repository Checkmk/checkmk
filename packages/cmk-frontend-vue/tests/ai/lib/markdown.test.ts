/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { extractQualityLevel, parseMarkdown, stripQualityLineFromText } from '@/ai/lib/markdown'

function badge(state: 'ok' | 'warn' | 'crit' | 'unknown'): string {
  const label = state.toUpperCase()
  return `<span class="ai-markdown-content__badge ai-markdown-content__badge--${state}">${label}</span>`
}

function tableWithBodyCell(cell: string): string {
  return ['| Service |', '|---------|', `| ${cell} |`, ''].join('\n')
}

async function parse(md: string): Promise<string> {
  return await parseMarkdown(md)
}

describe('markdown.parse - state badges in tables', () => {
  test.each([
    ['ok', 'ok'],
    ['warn', 'warn'],
    ['crit', 'crit'],
    ['unknown', 'unknown']
  ] as const)('replaces body cell %s with the matching badge', async (input, state) => {
    const html = await parse(tableWithBodyCell(input))
    expect(html).toContain(badge(state))
  })

  test.each(['OK', 'Ok', 'oK'])(
    'matches case-insensitively and renders an uppercase label (%s)',
    async (input) => {
      const html = await parse(tableWithBodyCell(input))
      expect(html).toContain(badge('ok'))
    }
  )

  test('replaces a bold-wrapped state word', async () => {
    const html = await parse(tableWithBodyCell('**crit**'))
    expect(html).toContain(badge('crit'))
    expect(html).not.toContain('<strong>')
  })

  test('tolerates surrounding whitespace inside the cell', async () => {
    const html = await parse(tableWithBodyCell('   warn   '))
    expect(html).toContain(badge('warn'))
  })

  test('replaces multiple state cells in the same row independently', async () => {
    const md = ['| A | B | C |', '|---|---|---|', '| ok | warn | crit |', ''].join('\n')
    const html = await parse(md)
    expect(html).toContain(badge('ok'))
    expect(html).toContain(badge('warn'))
    expect(html).toContain(badge('crit'))
  })
})

describe('markdown.parse - cells that must NOT be badged', () => {
  test.each(['okay', 'ok now', 'not ok', 'The status is ok.', ''])(
    'leaves non-matching cell text unchanged: %j',
    async (cell) => {
      const html = await parse(tableWithBodyCell(cell))
      expect(html).not.toContain('ai-markdown-content__badge')
    }
  )

  // Pin the asterisk balance behavior: only fully-paired `**state**` is
  // accepted as the bold form. Single, unclosed, and triple-asterisk
  // wrappings around a state word stay as plain (or italic / bold-italic)
  // markdown text.
  test.each(['**ok', 'ok**', '*ok*', '***ok***'])(
    'rejects malformed asterisk wrapping around a state word: %j',
    async (cell) => {
      const html = await parse(tableWithBodyCell(cell))
      expect(html).not.toContain('ai-markdown-content__badge')
    }
  )
})

describe('markdown.parse - scope of replacement', () => {
  test('does NOT badge header cells', async () => {
    const md = ['| OK |', '|----|', '| something |', ''].join('\n')
    const html = await parse(md)
    expect(html).toMatch(/<thead>[\s\S]*<th[^>]*>OK<\/th>[\s\S]*<\/thead>/)
    expect(html).not.toContain('ai-markdown-content__badge')
  })

  test('does NOT badge state words outside any table', async () => {
    const html = await parse('A paragraph that just says ok.\n\n- ok\n- warn\n')
    expect(html).not.toContain('ai-markdown-content__badge')
  })
})

describe('markdown - constructor options', () => {
  test('breaks: true converts single newlines into <br>', async () => {
    const html = await parse('first line\nsecond line')
    expect(html).toContain('<br>')
  })
})

describe('markdown.parse - representative explain_this_service output', () => {
  // Mirrors the table shape produced by the ai_service `explain_this_service`
  // prompt (see explain_this_service_prompt.py): a 3-column "Metric | Value |
  // Status" table where the Status column holds a state word or a literal "--"
  // placeholder for rows without a state.
  test('badges state cells, preserves "--" placeholders and free-text values', async () => {
    const md = [
      '# Summary',
      '',
      'The root filesystem is in **WARN** state, having crossed the 80% usage threshold.',
      '',
      '| Metric       | Value | Status |',
      '|--------------|-------|--------|',
      '| Used         | 82 %  | WARN   |',
      '| Available    | 18 GB | --     |',
      '| Inodes used  | 45 %  | OK     |',
      '',
      'Confidence: **High**',
      ''
    ].join('\n')
    const html = await parse(stripQualityLineFromText(md))

    expect(html).toContain(badge('warn'))
    expect(html).toContain(badge('ok'))

    // "--" placeholder cells must not be badged.
    expect(html).not.toContain(badge('crit'))
    expect(html).not.toContain(badge('unknown'))
    expect(html).toMatch(/<td[^>]*>--<\/td>/)

    // Free-text values survive intact.
    expect(html).toContain('82 %')
    expect(html).toContain('18 GB')
    expect(html).toContain('Inodes used')

    // Bold state word in the inline summary stays bold and is NOT badged.
    expect(html).toContain('<strong>WARN</strong>')

    expect(html).not.toContain('Confidence:')
  })

  test.each([
    [
      'no blank line before the marker',
      'The answer body.\nData Quality: **High**\n',
      'The answer body.'
    ],
    [
      'marker as its own paragraph',
      'The answer body.\n\nData Quality: **High**\n',
      'The answer body.'
    ],
    [
      'marker precedes body text',
      'Data Quality: **High**\n\nBody after the marker.\n',
      'Body after the marker.'
    ]
  ])('stripQualityLineFromText removes the quality line (%s)', (_desc, md, retainedBody) => {
    const stripped = stripQualityLineFromText(md)

    expect(stripped).toContain(retainedBody)
    expect(stripped).not.toContain('Data Quality:')
  })

  test('parseMarkdown never strips the quality line — stripping happens before parsing', async () => {
    const md = ['The answer body.', '', 'Data Quality: **High**', ''].join('\n')
    const html = await parse(md)

    expect(html).toContain('The answer body.')
    expect(html).toContain('Data Quality:')
  })
})

describe('markdown.parse - special list tagging', () => {
  test('adds service-context class to the ul after a "Service context" heading', async () => {
    const md = ['# Service context', '', '* item one', '* item two', ''].join('\n')
    const html = await parse(md)
    expect(html).toContain('class="ai-markdown-content__service-context"')
  })

  test('adds recommended-actions class to the ol after a "Recommended actions" heading', async () => {
    const md = ['# Recommended actions', '', '1. step one', '2. step two', ''].join('\n')
    const html = await parse(md)
    expect(html).toContain('class="ai-markdown-content__recommended-actions"')
  })

  test('tags a special list in a document whose quality line has been stripped', async () => {
    const md = [
      '# Service context',
      '',
      '* item one',
      '* item two',
      '',
      'Data Quality: **High**',
      ''
    ].join('\n')
    const html = await parse(stripQualityLineFromText(md))

    expect(html).toContain('class="ai-markdown-content__service-context"')
    expect(html).not.toContain('Data Quality:')
  })

  test('matching is case-insensitive for the heading text', async () => {
    const md = ['# SERVICE CONTEXT', '', '* item', ''].join('\n')
    const html = await parse(md)
    expect(html).toContain('class="ai-markdown-content__service-context"')
  })
})

describe('extractQualityLevel', () => {
  test.each([
    ['canonical High', 'Data Quality: **High**', 'high'],
    ['Medium', 'Data Quality: **Medium**', 'medium'],
    ['Low', 'Data Quality: **Low**', 'low'],
    ['legacy Confidence label', 'Confidence: **High**', 'high'],
    ['lowercase label and level', 'data quality: **low**', 'low'],
    ['leading whitespace and tab', '\t  Data Quality: **Medium**', 'medium'],
    ['marker among other lines', 'Answer body.\n\nData Quality: **Low**\n', 'low']
  ])('parses the level from %s', (_desc, text, expected) => {
    expect(extractQualityLevel(text)).toBe(expected)
  })

  test.each([
    ['no marker', 'Just an answer with no quality line.'],
    ['unbolded level', 'Data Quality: High'],
    ['unknown level word', 'Data Quality: **Unknown**'],
    ['label not on its own line', 'The Data Quality: **High** is inline here'],
    ['empty string', '']
  ])('returns null for %s', (_desc, text) => {
    expect(extractQualityLevel(text)).toBeNull()
  })
})

describe('stripQualityLineFromText - single-strip invariant', () => {
  test('removes only the first of two quality lines', () => {
    const text = ['Data Quality: **High**', '', 'Body.', '', 'Data Quality: **Low**', ''].join('\n')
    const stripped = stripQualityLineFromText(text)

    const remaining = stripped.match(/Data Quality:/g) ?? []
    expect(remaining).toHaveLength(1)
    expect(stripped).toContain('Data Quality: **Low**')
    expect(stripped).toContain('Body.')
  })
})
