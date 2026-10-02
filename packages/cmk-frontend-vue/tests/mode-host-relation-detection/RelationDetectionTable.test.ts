/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { expect, test } from 'vitest'

import RelationDetectionTable from '@/mode-host-relation-detection/RelationDetectionTable.vue'
import type { RelationRow } from '@/mode-host-relation-detection/types'

const RELATION_TITLES = { management_parent: 'is management board of' }

const PROPOSED: RelationRow = {
  key: 'srv-01-ilo|management|srv-01',
  finding: 'word:ilo',
  source_host: 'srv-01-ilo',
  target_host: 'srv-01',
  kind: 'management',
  relation: 'management_parent',
  folders: ['', ''],
  evidence: 'The name is "srv-01" with "ilo" added.',
  reason: { word: 'ilo', source: null, name: null, value: null },
  outcome: 'link',
  detail: ''
}

function renderTable(
  rows: RelationRow[],
  { selectable = true, done = false, excluded = new Map<string, string>() } = {}
) {
  return render(RelationDetectionTable, {
    props: { rows, relationTitles: RELATION_TITLES, done, selectable, excluded }
  })
}

test('a relation reads as the sentence it stands for', () => {
  renderTable([PROPOSED])

  screen.getByText('srv-01-ilo')
  screen.getByText('is management board of')
  screen.getByText('srv-01')
})

test('a relation says in short what speaks for it, and in full on hovering', () => {
  renderTable([PROPOSED])

  expect(screen.getByRole('cell', { name: '"ilo" in the name' })).toHaveAttribute(
    'title',
    'The name is "srv-01" with "ilo" added.'
  )
})

test('a relation found by a shared value shows the value the way a label reads', () => {
  renderTable([
    {
      ...PROPOSED,
      reason: { word: null, source: 'label', name: 'cmdb/sn', value: 'S-1' }
    }
  ])

  screen.getByText('cmdb/sn:S-1')
})

test('only a relation that can be stored can be taken out', () => {
  renderTable([
    PROPOSED,
    {
      ...PROPOSED,
      key: 'srv-02-ilo|management|srv-02',
      source_host: 'srv-02-ilo',
      target_host: 'srv-02',
      outcome: 'stored_otherwise',
      detail: '"srv-02-ilo" and "srv-02" are already related in another way.'
    }
  ])

  expect(screen.getAllByRole('checkbox')).toHaveLength(1)
  screen.getByText('Related in another way')
})

test('taking a relation out says which one', async () => {
  const { emitted } = renderTable([PROPOSED])

  await userEvent.click(
    screen.getByRole('checkbox', { name: 'srv-01-ilo is management board of srv-01' })
  )

  expect(emitted('toggle')).toEqual([[PROPOSED, false]])
})

test('a relation taken out shows as such', () => {
  renderTable([PROPOSED], { excluded: new Map([[PROPOSED.key, PROPOSED.finding]]) })

  expect(
    screen.getByRole('checkbox', { name: 'srv-01-ilo is management board of srv-01' })
  ).not.toBeChecked()
})

test('what a run did is not something to pick from', () => {
  renderTable([PROPOSED], { selectable: false, done: true })

  expect(screen.queryByRole('checkbox')).toBeNull()
  screen.getByText('Stored')
})
