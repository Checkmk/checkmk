/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
import { describe, expect, it } from 'vitest'

import VisibilitySettings from '@/dashboard/components/Wizard/wizards/dashboard-settings/components/VisibilitySettings.vue'

import { mainMenuTopicsHandler, useAnsweredRequestsAfterEach } from '@tests/dashboard/apiHandlers'

const server = useMswServer(
  mainMenuTopicsHandler([
    { id: 'monitoring', title: 'Monitoring', sortIndex: 0, isDefault: true },
    { id: 'problems', title: 'Problems', sortIndex: 1, isDefault: false }
  ])
)
useAnsweredRequestsAfterEach(server)

const defaultProps = {
  hideInMonitorMenu: false,
  monitorMenuTopic: 'monitoring',
  sortIndex: 10,
  hideInDropdownsMenu: false,
  showWhenShowMoreIsEnabled: false,
  sortIndexError: [] as string[]
}

function renderVisibilitySettings(overrides: Record<string, unknown> = {}) {
  return render(VisibilitySettings, { props: { ...defaultProps, ...overrides } })
}

describe('VisibilitySettings', () => {
  describe('Dropdown checkbox (inverted hideInDropdownsMenu)', () => {
    it('renders checked when hideInDropdownsMenu is false', () => {
      renderVisibilitySettings({ hideInDropdownsMenu: false })
      const checkbox = screen.getByRole('checkbox', {
        name: 'Show in dashboard name dropdown'
      })
      expect(checkbox).toBeChecked()
    })

    it('renders unchecked when hideInDropdownsMenu is true', () => {
      renderVisibilitySettings({ hideInDropdownsMenu: true })
      const checkbox = screen.getByRole('checkbox', {
        name: 'Show in dashboard name dropdown'
      })
      expect(checkbox).not.toBeChecked()
    })

    it('emits inverted value when checkbox is clicked', async () => {
      const { emitted } = renderVisibilitySettings({ hideInDropdownsMenu: false })
      const checkbox = screen.getByRole('checkbox', {
        name: 'Show in dashboard name dropdown'
      })
      await fireEvent.click(checkbox)
      expect(emitted()['update:hideInDropdownsMenu']![0]).toEqual([true])
    })
  })

  describe('Show more checkbox', () => {
    it('renders unchecked when showWhenShowMoreIsEnabled is false', () => {
      renderVisibilitySettings({ showWhenShowMoreIsEnabled: false })
      const checkbox = screen.getByRole('checkbox', {
        name: 'Only show when "Show more" is enabled'
      })
      expect(checkbox).not.toBeChecked()
    })

    it('renders checked when showWhenShowMoreIsEnabled is true', () => {
      renderVisibilitySettings({ showWhenShowMoreIsEnabled: true })
      const checkbox = screen.getByRole('checkbox', {
        name: 'Only show when "Show more" is enabled'
      })
      expect(checkbox).toBeChecked()
    })

    it('emits true when clicked', async () => {
      const { emitted } = renderVisibilitySettings({ showWhenShowMoreIsEnabled: false })
      const checkbox = screen.getByRole('checkbox', {
        name: 'Only show when "Show more" is enabled'
      })
      await fireEvent.click(checkbox)
      expect(emitted()['update:showWhenShowMoreIsEnabled']![0]).toEqual([true])
    })
  })
})
