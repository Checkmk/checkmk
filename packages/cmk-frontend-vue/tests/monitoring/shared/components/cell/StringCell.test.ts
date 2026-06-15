/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { defineComponent, h } from 'vue'

import StringCell from '@/monitoring/shared/components/cell/StringCell.vue'

function mountCell(value: string | undefined) {
  return render(
    defineComponent({
      render() {
        return h('table', [h('tbody', [h('tr', [h(StringCell, { value })])])])
      }
    })
  )
}

test('renders the value as cell text', () => {
  mountCell('web-1')

  expect(screen.getByTitle('web-1')).toBeInTheDocument()
})

test('renders a placeholder instead of crashing when the value is missing', () => {
  const { container } = mountCell(undefined)

  const cell = container.querySelector('td')
  expect(cell).not.toBeNull()
  expect(cell).toHaveTextContent('n/a')
})
