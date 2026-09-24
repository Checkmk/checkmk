/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import axios from 'axios'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'

import DashboardContentNtop from '@/dashboard/components/DashboardContent/DashboardContentNtop.vue'
import { useProvideIsPublicDashboard } from '@/dashboard/composables/useIsPublicDashboard'

import { makeContentProps } from '@tests/dashboard/contentProps'

import { flushPromises } from '../../utils.ts'

vi.mock('axios')
const mockedAxiosGet = vi.mocked(axios.get)

const baseProps = makeContentProps(
  { type: 'ntop_top_talkers' as const },
  {
    widget_id: 'w1',
    general_settings: {
      title: { text: 'ntop', render_mode: 'with_background' },
      render_background: true
    },
    effectiveTitle: 'ntop top talkers'
  }
)

function renderInPublicDashboard() {
  const wrapper = defineComponent({
    setup() {
      useProvideIsPublicDashboard()
      return () => h(DashboardContentNtop, baseProps as never)
    }
  })
  return render(wrapper)
}

describe('DashboardContentNtop', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the "Not available" placeholder on a shared dashboard', async () => {
    renderInPublicDashboard()
    await flushPromises()
    expect(screen.getByText('Not available on shared dashboards')).toBeInTheDocument()
  })

  it('does not call axios on a shared dashboard', async () => {
    renderInPublicDashboard()
    await flushPromises()
    expect(mockedAxiosGet).not.toHaveBeenCalled()
  })
})
