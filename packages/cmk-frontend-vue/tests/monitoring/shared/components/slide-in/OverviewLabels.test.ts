/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'

import OverviewLabels from '@/monitoring/shared/components/slide-in/OverviewLabels.vue'

test('sets the value of a label in bold, apart from its key', () => {
  render(OverviewLabels, {
    props: { labels: { 'cmk/os_family': { value: 'linux', source: 'discovered' } } }
  })

  expect(screen.getByText('linux').tagName).toBe('STRONG')
  expect(screen.getByText(/cmk\/os_family:/)).toHaveTextContent('cmk/os_family: linux')
})
