/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { defineComponent, ref } from 'vue'

import type { ColumnFilterNode } from '@/monitoring/shared/api/types'
import FilterStringInput from '@/monitoring/shared/components/filter/FilterStringInput.vue'
import type { StringInputFilter } from '@/monitoring/shared/components/filter/types'

const definition: StringInputFilter<'name'> = { type: 'string-input', field: 'name' }

test('the free-text field is reachable by name', () => {
  const model = ref<ColumnFilterNode<'name'> | undefined>(undefined)
  render(
    defineComponent({
      components: { FilterStringInput },
      setup() {
        return { model, definition }
      },
      template: '<FilterStringInput v-model="model" :definition="definition" />'
    })
  )

  expect(screen.getByRole('textbox', { name: 'Value' })).toBeInTheDocument()
})
