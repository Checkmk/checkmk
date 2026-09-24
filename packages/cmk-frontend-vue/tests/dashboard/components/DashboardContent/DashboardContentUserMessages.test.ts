/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'

import DashboardContentUserMessages from '@/dashboard/components/DashboardContent/DashboardContentUserMessages.vue'
import { useProvideIsPublicDashboard } from '@/dashboard/composables/useIsPublicDashboard'

import { makeContentProps } from '@tests/dashboard/contentProps'

import { flushPromises } from '../../utils.ts'

const mockCmkAjax = vi.hoisted(() => vi.fn().mockResolvedValue([]))

vi.mock('cmk-ui-library/lib/ajax', () => ({
  cmkAjax: mockCmkAjax
}))

const baseProps = makeContentProps(
  { type: 'user_messages' as const },
  {
    widget_id: 'w1',
    general_settings: {
      title: { text: 'User messages', render_mode: 'with_background' },
      render_background: true
    },
    effectiveTitle: 'User messages'
  }
)

function renderInPublicDashboard() {
  const wrapper = defineComponent({
    setup() {
      useProvideIsPublicDashboard()
      return () => h(DashboardContentUserMessages, baseProps as never)
    }
  })
  return render(wrapper)
}

function renderInPrivateDashboard() {
  return render(DashboardContentUserMessages, { props: baseProps as never })
}

describe('DashboardContentUserMessages', () => {
  beforeEach(() => {
    mockCmkAjax.mockClear()
  })

  it('renders the "Not available" placeholder on a shared dashboard', async () => {
    renderInPublicDashboard()
    await flushPromises()
    expect(screen.getByText('Not available on shared dashboards')).toBeInTheDocument()
  })

  it('does not call cmkAjax on a shared dashboard', async () => {
    renderInPublicDashboard()
    await flushPromises()
    expect(mockCmkAjax).not.toHaveBeenCalled()
  })

  it('fetches messages from ajax_get_user_messages.py on a non-shared dashboard', async () => {
    renderInPrivateDashboard()
    await flushPromises()
    expect(mockCmkAjax).toHaveBeenCalledWith('ajax_get_user_messages.py', {})
  })

  it('renders the empty-state message when there are no messages', async () => {
    mockCmkAjax.mockResolvedValueOnce([])
    renderInPrivateDashboard()
    await flushPromises()
    expect(screen.getByText('Currently you have no received messages')).toBeInTheDocument()
  })
})
