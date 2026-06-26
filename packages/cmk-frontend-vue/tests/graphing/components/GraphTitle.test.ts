/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'

import GraphTitle from '@/graphing/components/GraphTitle.vue'

test('renders the title text', () => {
  render(GraphTitle, { props: { title: 'CPU utilization' } })
  expect(screen.getByText('CPU utilization')).toBeInTheDocument()
})

test('renders without error when title is an empty string', () => {
  render(GraphTitle, { props: { title: '' } })
  expect(document.querySelector('.graphing-graph-title')).toBeInTheDocument()
})
