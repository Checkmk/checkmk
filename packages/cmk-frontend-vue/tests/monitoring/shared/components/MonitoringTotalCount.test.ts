/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'

import MonitoringTotalCount from '@/monitoring/shared/components/MonitoringTotalCount.vue'

test('shows the total row count', () => {
  render(MonitoringTotalCount, { props: { total: 5151 } })

  expect(screen.getByText('Total rows: 5151')).toBeInTheDocument()
})

test('shows nothing when there are no rows at all', () => {
  const { container } = render(MonitoringTotalCount, { props: { total: 0 } })

  expect(container.querySelector('.monitoring-total-count')).not.toBeInTheDocument()
})
