/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { describe, expect, it, vi } from 'vitest'

import VisibilityProperties from '@/dashboard/components/Wizard/components/DashboardSettings/VisibilityProperties.vue'

vi.mock('@/dashboard/utils', () => ({
  dashboardAPI: {
    listMainMenuTopics: vi.fn().mockResolvedValue([
      { id: 'monitoring', title: 'Monitoring', sortIndex: 1, isDefault: true },
      { id: 'other', title: 'Other', sortIndex: 2, isDefault: false }
    ])
  }
}))

describe('VisibilityProperties', () => {
  describe('Rendering', () => {
    it('renders the "Dashboard visibility" field description', async () => {
      render(VisibilityProperties, {
        props: { showInMonitorMenu: false, monitorMenuTopic: '', sortIndex: 99, sortIndexError: [] }
      })
      expect(await screen.findByText('Dashboard visibility')).toBeInTheDocument()
    })

    it('renders the "Sort index" field description', async () => {
      render(VisibilityProperties, {
        props: { showInMonitorMenu: false, monitorMenuTopic: '', sortIndex: 99, sortIndexError: [] }
      })
      expect(await screen.findByText('Sort index')).toBeInTheDocument()
    })

    it('renders the sort index input with the provided value', async () => {
      render(VisibilityProperties, {
        props: { showInMonitorMenu: false, monitorMenuTopic: '', sortIndex: 42, sortIndexError: [] }
      })
      const input = await screen.findByDisplayValue('42')
      expect(input).toBeInTheDocument()
    })

    it('renders error message when sortIndexError is provided', async () => {
      render(VisibilityProperties, {
        props: {
          showInMonitorMenu: false,
          monitorMenuTopic: '',
          sortIndex: -1,
          sortIndexError: ['Sort index must be a positive integer']
        }
      })
      expect(await screen.findByText('Sort index must be a positive integer')).toBeInTheDocument()
    })

    it('renders slotted extra-visibility-settings content', async () => {
      render(VisibilityProperties, {
        props: {
          showInMonitorMenu: false,
          monitorMenuTopic: '',
          sortIndex: 99,
          sortIndexError: []
        },
        slots: { 'extra-visibility-settings': '<span>Extra setting</span>' }
      })
      expect(await screen.findByText('Extra setting')).toBeInTheDocument()
    })
  })

  describe('Events', () => {
    it('emits update:sortIndex when sort index input changes', async () => {
      const { emitted } = render(VisibilityProperties, {
        props: { showInMonitorMenu: false, monitorMenuTopic: '', sortIndex: 99, sortIndexError: [] }
      })
      const input = await screen.findByDisplayValue('99')
      await fireEvent.update(input, '10')
      expect(emitted()['update:sortIndex']).toBeDefined()
    })

    it('emits update:showInMonitorMenu when checkbox is toggled', async () => {
      const { emitted } = render(VisibilityProperties, {
        props: { showInMonitorMenu: false, monitorMenuTopic: '', sortIndex: 99, sortIndexError: [] }
      })
      const checkbox = await screen.findByLabelText('Show in monitor menu')
      await fireEvent.click(checkbox)
      expect(emitted()['update:showInMonitorMenu']).toEqual([[true]])
    })
  })
})
