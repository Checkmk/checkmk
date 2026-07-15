/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'

import FormGroupBy from '@/metric-backend/group-by/FormGroupBy.vue'
import type { GroupByModel } from '@/metric-backend/group-by/types'

test('the collapsed chip summarises the clause', () => {
  const model: GroupByModel = {
    function: 'avg',
    params: {},
    keys: [{ id: '1', level: 'resource', key: 'service.name' }]
  }
  render(FormGroupBy, { props: { modelValue: model } })
  expect(screen.getByText('avg by [Resource] service.name')).toBeVisible()
})
