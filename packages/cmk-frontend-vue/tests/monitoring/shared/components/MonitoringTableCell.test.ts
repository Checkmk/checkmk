/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { defineComponent, h } from 'vue'

import MonitoringTableCell from '@/monitoring/shared/components/MonitoringTableCell.vue'

function mountCell(props: { breakpoint?: 's' | 'm' | 'l' | 'xl' }) {
  return render(
    defineComponent({
      components: { MonitoringTableCell },
      render() {
        return h('table', [
          h('tbody', [h('tr', [h(MonitoringTableCell, props, () => 'cell content')])])
        ])
      }
    })
  )
}

test('renders a <td> with cell content', () => {
  const { container } = mountCell({})
  const td = container.querySelector('td')
  expect(td).not.toBeNull()
  expect(td).toHaveTextContent('cell content')
})

test('attaches the breakpoint class when breakpoint is set', () => {
  const { container } = mountCell({ breakpoint: 'l' })
  expect(container.querySelector('.monitoring-table-cell--breakpoint-l')).not.toBeNull()
})

test('omits the breakpoint class when breakpoint is unset', () => {
  const { container } = mountCell({})
  expect(container.querySelector('[class*="monitoring-table-cell--breakpoint"]')).toBeNull()
})
