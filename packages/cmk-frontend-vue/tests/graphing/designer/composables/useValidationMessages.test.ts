/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { defineComponent } from 'vue'

import { useValidationMessages } from '@/graphing/designer/composables/useValidationMessages'
import type { RowIssue } from '@/graphing/designer/validation'

function mountMessages(): ReturnType<typeof useValidationMessages> {
  let api!: ReturnType<typeof useValidationMessages>
  render(
    defineComponent({
      setup() {
        api = useValidationMessages()
        return () => null
      }
    })
  )
  return api
}

/** Keyed by code, so a new code fails to compile without a message. */
const CASES: Record<RowIssue['code'], { issue: RowIssue; message: string }> = {
  required: {
    issue: { id: 'A', field: 'metric_name', code: 'required' },
    message: 'This field is required.'
  },
  'filter-required': {
    issue: { id: 'A', field: 'host_filter', code: 'filter-required' },
    message: 'Fill in at least one filter.'
  },
  'not-finite': {
    issue: { id: 'A', field: 'value', code: 'not-finite' },
    message: 'Enter a finite number.'
  },
  'lookback-too-small': {
    issue: { id: 'A', field: 'consolidation_function', code: 'lookback-too-small' },
    message: 'The lookback must be at least one second.'
  },
  'percentile-out-of-range': {
    issue: { id: 'A', field: 'consolidation_function', code: 'percentile-out-of-range' },
    message: 'The percentile must be between 0 and 100.'
  },
  'thresholds-unordered': {
    issue: { id: 'A', field: 'consolidation_function', code: 'thresholds-unordered' },
    message: 'The lower threshold must be below the upper threshold.'
  },
  'ref-incomplete': {
    issue: { id: 'A', field: 'ast', code: 'ref-incomplete', ref: 'B' },
    message: '"B" is not configured yet.'
  },
  'unknown-ref': {
    issue: { id: 'A', field: 'ast', code: 'unknown-ref', ref: 'B' },
    message: 'Unknown metric or formula "B".'
  },
  'self-ref': {
    issue: { id: 'A', field: 'ast', code: 'self-ref', ref: 'A' },
    message: 'The formula cannot reference itself ("A").'
  },
  'cyclic-ref': {
    issue: { id: 'A', field: 'ast', code: 'cyclic-ref', ref: 'B' },
    message: '"B" refers back to this formula (circular reference).'
  },
  'domain-mismatch': {
    issue: { id: 'A', field: 'ast', code: 'domain-mismatch', ref: 'B' },
    message: 'Cannot mix RRD and metrics backend data: "B".'
  },
  'needs-consolidation': {
    issue: { id: 'A', field: 'ast', code: 'needs-consolidation', ref: 'B' },
    message: 'Consolidate "B" using avg, min, max or sum.'
  }
}

test.each(Object.entries(CASES))('%s states its own reason', (_code, { issue, message }) => {
  expect(mountMessages().issueMessage(issue)).toBe(message)
})

test('no two issue codes share a message', () => {
  const { issueMessage } = mountMessages()
  const messages = Object.values(CASES).map(({ issue }) => issueMessage(issue))
  expect(new Set(messages).size).toBe(messages.length)
})
