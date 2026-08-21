/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { defineComponent, h } from 'vue'

import type { EventIcon, HostMode, MonitoringIcon } from '@/monitoring/shared/api/types'
import IconCell from '@/monitoring/shared/components/cell/IconCell.vue'

const DOWNTIME_MODE: HostMode = {
  icon_name: 'downtime',
  link: 'view.py?view_name=downtimes_of_host&host=web-1',
  title: 'In scheduled downtime'
}

const ACKNOWLEDGED_MODE: HostMode = {
  icon_name: 'ack',
  link: 'view.py?view_name=host&host=web-1',
  title: 'Problem acknowledged'
}

const SERVICE_ALERT_EVENT: EventIcon = {
  icon_name: 'alert-crit',
  title: 'Service alert'
}

function mountCell(icons: MonitoringIcon[]) {
  return render(
    defineComponent({
      render() {
        return h('table', [h('tbody', [h('tr', [h(IconCell, { icons })])])])
      }
    })
  )
}

test('renders a linked icon per mode, in the order given', () => {
  mountCell([DOWNTIME_MODE, ACKNOWLEDGED_MODE])

  const downtime = screen.getByRole('link', { name: 'In scheduled downtime' })
  const acknowledged = screen.getByRole('link', { name: 'Problem acknowledged' })

  expect(downtime).toHaveAttribute('href', 'view.py?view_name=downtimes_of_host&host=web-1')
  expect(acknowledged).toHaveAttribute('href', 'view.py?view_name=host&host=web-1')
  expect(downtime.compareDocumentPosition(acknowledged)).toBe(Node.DOCUMENT_POSITION_FOLLOWING)
})

test('renders an icon without a link as read-only', () => {
  mountCell([SERVICE_ALERT_EVENT])

  expect(screen.getByRole('img', { name: 'Service alert' })).toBeInTheDocument()
  expect(screen.queryByRole('link')).not.toBeInTheDocument()
})

test('renders linked and read-only icons side by side', () => {
  mountCell([DOWNTIME_MODE, SERVICE_ALERT_EVENT])

  expect(screen.getAllByRole('link')).toHaveLength(1)
  expect(screen.getByRole('img', { name: 'Service alert' })).toBeInTheDocument()
})

test('renders nothing for an empty icon list', () => {
  mountCell([])

  expect(screen.queryByRole('link')).not.toBeInTheDocument()
})
