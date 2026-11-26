/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CalendarDateTime, toZoned } from '@internationalized/date'
import { fireEvent, render, screen } from '@testing-library/vue'
import type { GlobalTimePickerProps } from 'cmk-shared-typing/typescript/global_time_picker'
import type { DateTimeRange } from 'cmk-ui-library/components/date-time/types.ts'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import SharedDashboardMenuHeader from '@/dashboard/components/DashboardMenuHeader/SharedDashboardMenuHeader.vue'
import { resetGlobalTimeState } from '@/graphing/GlobalTimePicker/globalTimeState'

const TZ = 'Europe/Berlin'

const testRange: DateTimeRange = (() => {
  const to = toZoned(new CalendarDateTime(2026, 3, 10, 12, 0), TZ, 'compatible')
  return { from: to.subtract({ hours: 4 }), to }
})()

const testGlobalTimePicker: GlobalTimePickerProps = {
  custom_time_ranges: [{ title: 'Last 1 hour', total_seconds: 3600 }],
  default_time_range: 4 * 3600,
  server_time_zone: TZ,
  first_day_of_week: null,
  refresh: {
    interval_seconds: null,
    interval_choices_seconds: [30, 60, 90],
    starts_live: true,
    reloads_page_content: false
  }
}

const TIME_PICKER_TOGGLE = 'Show date time picker'
const REFRESH_TOGGLE = 'Show live refresh'

function renderSharedHeader(props: { dashboardTitle: string }) {
  return render(SharedDashboardMenuHeader, {
    props: { ...props, globalTimePicker: testGlobalTimePicker, range: testRange }
  })
}

function timePicker(): Element | null {
  return document.querySelector('.graphing-global-time-picker')
}

function refreshControl(): Element | null {
  return document.querySelector('.graphing-global-refresh-control')
}

async function clickMenuItem(label: string) {
  await fireEvent.click(screen.getByLabelText('Settings Menu'))
  await fireEvent.click(screen.getByText(label))
}

describe('SharedDashboardMenuHeader', () => {
  // The global time/refresh state is a module-level singleton.
  beforeEach(() => {
    resetGlobalTimeState()
  })

  afterEach(() => {
    resetGlobalTimeState()
  })

  describe('rendering', () => {
    it('renders the dashboard title', () => {
      renderSharedHeader({ dashboardTitle: 'My Shared Dashboard' })
      expect(screen.getByText('My Shared Dashboard')).toBeInTheDocument()
    })

    it('shows the time picker and the live refresh by default', () => {
      renderSharedHeader({ dashboardTitle: 'Test' })
      expect(timePicker()).not.toBeNull()
      expect(refreshControl()).not.toBeNull()
    })
  })

  describe('settings menu', () => {
    it('does not show menu by default', () => {
      renderSharedHeader({ dashboardTitle: 'Test' })
      expect(screen.queryByText(TIME_PICKER_TOGGLE)).not.toBeInTheDocument()
      expect(screen.queryByText(REFRESH_TOGGLE)).not.toBeInTheDocument()
    })

    it('opens settings menu when menu button is clicked', async () => {
      renderSharedHeader({ dashboardTitle: 'Test' })
      await fireEvent.click(screen.getByLabelText('Settings Menu'))
      expect(screen.getByText(TIME_PICKER_TOGGLE)).toBeInTheDocument()
      expect(screen.getByText(REFRESH_TOGGLE)).toBeInTheDocument()
    })

    it('closes settings menu when menu button is clicked again', async () => {
      renderSharedHeader({ dashboardTitle: 'Test' })
      const menuButton = screen.getByLabelText('Settings Menu')
      await fireEvent.click(menuButton)
      expect(screen.getByText(TIME_PICKER_TOGGLE)).toBeInTheDocument()
      await fireEvent.click(menuButton)
      expect(screen.queryByText(TIME_PICKER_TOGGLE)).not.toBeInTheDocument()
    })

    it('sets aria-expanded correctly on menu toggle', async () => {
      renderSharedHeader({ dashboardTitle: 'Test' })
      const menuButton = screen.getByLabelText('Settings Menu')
      expect(menuButton).toHaveAttribute('aria-expanded', 'false')
      await fireEvent.click(menuButton)
      expect(menuButton).toHaveAttribute('aria-expanded', 'true')
    })

    it('closes the menu after selecting an item', async () => {
      renderSharedHeader({ dashboardTitle: 'Test' })
      await clickMenuItem(TIME_PICKER_TOGGLE)
      expect(screen.queryByText(TIME_PICKER_TOGGLE)).not.toBeInTheDocument()
    })
  })

  describe('time picker toggle', () => {
    it('hides the time picker and keeps the live refresh', async () => {
      renderSharedHeader({ dashboardTitle: 'Test' })

      await clickMenuItem(TIME_PICKER_TOGGLE)

      expect(timePicker()).toBeNull()
      expect(refreshControl()).not.toBeNull()
    })

    it('shows the time picker again when toggled twice', async () => {
      renderSharedHeader({ dashboardTitle: 'Test' })

      await clickMenuItem(TIME_PICKER_TOGGLE)
      await clickMenuItem(TIME_PICKER_TOGGLE)

      expect(timePicker()).not.toBeNull()
    })
  })

  describe('live refresh toggle', () => {
    it('hides the live refresh and keeps the time picker', async () => {
      renderSharedHeader({ dashboardTitle: 'Test' })

      await clickMenuItem(REFRESH_TOGGLE)

      expect(refreshControl()).toBeNull()
      expect(timePicker()).not.toBeNull()
    })

    it('shows the live refresh again when toggled twice', async () => {
      renderSharedHeader({ dashboardTitle: 'Test' })

      await clickMenuItem(REFRESH_TOGGLE)
      await clickMenuItem(REFRESH_TOGGLE)

      expect(refreshControl()).not.toBeNull()
    })
  })

  it('hides both controls when both toggles are switched off', async () => {
    renderSharedHeader({ dashboardTitle: 'Test' })

    await clickMenuItem(TIME_PICKER_TOGGLE)
    await clickMenuItem(REFRESH_TOGGLE)

    expect(timePicker()).toBeNull()
    expect(refreshControl()).toBeNull()
  })
})
