/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { useHostActions } from '@/monitoring/shared/useHostActions'

test('keys every host command by its own ID', () => {
  const actions = useHostActions({})

  const keyedByAnotherId = Object.entries(actions.registry).filter(
    ([ident, action]) => action.id !== ident
  )

  expect(keyedByAnotherId).toEqual([])
})
