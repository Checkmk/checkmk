/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { defineComponent, h } from 'vue'

import type { CustomIcon, HostMode } from '@/monitoring/shared/api/types'
import IndicatorCell from '@/monitoring/shared/components/cell/IndicatorCell.vue'

const DOWNTIME_MODE: HostMode = {
  id: 'downtime',
  icon_name: 'downtime',
  link: 'view.py?view_name=downtimes_of_host&host=web-1',
  title: 'In scheduled downtime'
}

const customIcon = (ident: string, extra: Partial<CustomIcon> = {}): CustomIcon => ({
  ident,
  title: `Icon ${ident}`,
  icon_name: 'wiki',
  ...extra
})

function mountCell(modes: HostMode[], icons: CustomIcon[]) {
  return render(
    defineComponent({
      render() {
        return h('table', [h('tbody', [h('tr', [h(IndicatorCell, { modes, icons, max: 3 })])])])
      }
    })
  )
}

test('shows an uploaded custom icon from its path', () => {
  mountCell([], [customIcon('logo', { icon_path: 'images/icons/logo.png' })])

  expect(screen.getByRole('img', { name: 'Icon logo' })).toHaveAttribute(
    'src',
    'images/icons/logo.png'
  )
})

test('shows the custom icons after the modes', () => {
  mountCell([DOWNTIME_MODE], [customIcon('a')])

  const mode = screen.getByRole('link', { name: 'In scheduled downtime' })
  const icon = screen.getByRole('img', { name: 'Icon a' })
  expect(mode.compareDocumentPosition(icon)).toBe(Node.DOCUMENT_POSITION_FOLLOWING)
})

test('shows at most three indicators and counts the rest', () => {
  mountCell([DOWNTIME_MODE], [customIcon('a'), customIcon('b'), customIcon('c')])

  expect(screen.queryByRole('img', { name: 'Icon c' })).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Show all 4 indicators' })).toHaveTextContent('+1')
})

test('reveals the counted indicators on request', async () => {
  mountCell([DOWNTIME_MODE], [customIcon('a'), customIcon('b'), customIcon('c')])

  await userEvent.click(screen.getByRole('button', { name: 'Show all 4 indicators' }))

  expect(screen.getByRole('img', { name: 'Icon c' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'show less' })).toBeInTheDocument()
})
