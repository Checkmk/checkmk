/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { expect, test } from 'vitest'
import { computed } from 'vue'

import { useBlockingIssues } from '@/graphing/designer/composables/useBlockingIssues'
import { newRrdMetricDraft } from '@/graphing/designer/drafts'

import { rrdMetricItem } from '../fixtures'

function blockingIssuesOf(...items: Parameters<typeof useBlockingIssues>[0]['value']) {
  return useBlockingIssues(
    computed(() => items),
    () => null
  )
}

test('shows no issues at the rows before a save has been tried', () => {
  const { blockingIssues, issuesByRow } = blockingIssuesOf(newRrdMetricDraft('A', '#28a2f3'))

  expect(blockingIssues.value).not.toHaveLength(0)
  expect(issuesByRow.value.size).toBe(0)
})

test('shows each blocking issue at its row once a save has been tried', () => {
  const { blockingIssues, issuesByRow, hasAttemptedSave } = blockingIssuesOf(
    newRrdMetricDraft('A', '#28a2f3'),
    rrdMetricItem('B')
  )

  hasAttemptedSave.value = true

  expect([...issuesByRow.value.keys()]).toEqual(['A'])
  expect(issuesByRow.value.get('A')).toEqual(blockingIssues.value)
})
