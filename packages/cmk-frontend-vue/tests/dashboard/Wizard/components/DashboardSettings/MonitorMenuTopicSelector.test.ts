/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { describe, expect, it, vi } from 'vitest'

import MonitorMenuTopicSelector from '@/dashboard/components/Wizard/components/DashboardSettings/MonitorMenuTopicSelector.vue'

vi.mock('@/dashboard/utils', () => ({
  dashboardAPI: {
    listMainMenuTopics: vi.fn().mockResolvedValue([
      { id: 'monitoring', title: 'Monitoring', sortIndex: 1, isDefault: true },
      { id: 'other', title: 'Other', sortIndex: 2, isDefault: false },
      { id: 'network', title: 'Network', sortIndex: 0, isDefault: false }
    ])
  }
}))

describe('MonitorMenuTopicSelector', () => {
  describe('Rendering', () => {
    it('renders the "Show in monitor menu" checkbox', async () => {
      render(MonitorMenuTopicSelector, {
        props: { showInMonitorMenu: false, selectedTopic: '' }
      })
      expect(await screen.findByLabelText('Show in monitor menu')).toBeInTheDocument()
    })

    it('does not show dropdown when showInMonitorMenu is false', async () => {
      render(MonitorMenuTopicSelector, {
        props: { showInMonitorMenu: false, selectedTopic: '' }
      })
      await screen.findByLabelText('Show in monitor menu')
      expect(screen.queryByLabelText('Select option')).not.toBeInTheDocument()
    })

    it('shows dropdown when showInMonitorMenu is true', async () => {
      render(MonitorMenuTopicSelector, {
        props: { showInMonitorMenu: true, selectedTopic: 'monitoring' }
      })
      expect(await screen.findByLabelText('Select option')).toBeInTheDocument()
    })

    it('checkbox is unchecked when showInMonitorMenu is false', async () => {
      render(MonitorMenuTopicSelector, {
        props: { showInMonitorMenu: false, selectedTopic: '' }
      })
      const checkbox = await screen.findByLabelText('Show in monitor menu')
      expect(checkbox).not.toBeChecked()
    })

    it('checkbox is checked when showInMonitorMenu is true', async () => {
      render(MonitorMenuTopicSelector, {
        props: { showInMonitorMenu: true, selectedTopic: '' }
      })
      const checkbox = await screen.findByLabelText('Show in monitor menu')
      expect(checkbox).toBeChecked()
    })
  })

  describe('Topic loading', () => {
    it('sets selected topic to default when selectedTopic is empty', async () => {
      const { emitted } = render(MonitorMenuTopicSelector, {
        props: { showInMonitorMenu: true, selectedTopic: '' }
      })
      await screen.findByLabelText('Select option')
      expect(emitted()['update:selectedTopic']).toEqual([['monitoring']])
    })

    it('does not override selectedTopic when it is already set', async () => {
      const { emitted } = render(MonitorMenuTopicSelector, {
        props: { showInMonitorMenu: true, selectedTopic: 'other' }
      })
      await screen.findByLabelText('Select option')
      expect(emitted()['update:selectedTopic']).toBeUndefined()
    })
  })

  describe('Events', () => {
    it('emits update:showInMonitorMenu when checkbox is clicked', async () => {
      const { emitted } = render(MonitorMenuTopicSelector, {
        props: { showInMonitorMenu: false, selectedTopic: '' }
      })
      const checkbox = await screen.findByLabelText('Show in monitor menu')
      await fireEvent.click(checkbox)
      expect(emitted()['update:showInMonitorMenu']).toEqual([[true]])
    })
  })
})
