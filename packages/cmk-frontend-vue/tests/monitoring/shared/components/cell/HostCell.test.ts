/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { defineComponent, h } from 'vue'

import HostCell from '@/monitoring/shared/components/cell/HostCell.vue'

function mountCell(props: Record<string, unknown> = {}) {
  return render(
    defineComponent({
      render() {
        return h('table', [
          h('tbody', [h('tr', [h(HostCell, { name: 'web-1', state: 'UP', ...props })])])
        ])
      }
    })
  )
}

test('opens the host from a button', () => {
  mountCell()

  expect(screen.getByRole('button')).toHaveTextContent('web-1')
})

test('offers no button when it must not open the host', () => {
  mountCell({ button: false })

  expect(screen.queryByRole('button')).not.toBeInTheDocument()
})
