/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { expect, test } from 'vitest'

import { barActions } from '@/monitoring/shared/components/action/barActions'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'

function cellAction(id: string): CellAction {
  return { id, label: id as TranslatedString, icon: 'reload' }
}

test('acknowledge, downtime and reschedule are buttons, the rest goes to the menu', () => {
  const { bar, more } = barActions(
    ['acknowledge', 'add_comment', 'schedule_downtimes', 'reschedule'].map(cellAction)
  )

  expect(bar.map((action) => action.id)).toEqual([
    'acknowledge',
    'schedule_downtimes',
    'reschedule'
  ])
  expect(more.map((action) => action.id)).toEqual(['add_comment'])
})
