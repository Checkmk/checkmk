/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import { DashboardType } from '@/dashboard/components/Wizard/components/DashboardSettings/types'
import DashboardTypeSelector from '@/dashboard/components/Wizard/wizards/create-dashboard/components/DashboardTypeSelector.vue'

describe('DashboardTypeSelector', () => {
  describe('Rendering', () => {
    it('renders three type options', () => {
      render(DashboardTypeSelector, {
        props: { dashboardType: DashboardType.UNRESTRICTED }
      })
      expect(screen.getByRole('button', { name: 'Toggle Unrestricted' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Toggle Specific host' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Toggle Custom' })).toBeInTheDocument()
    })

    it('marks Unrestricted as selected when dashboardType is UNRESTRICTED', () => {
      render(DashboardTypeSelector, {
        props: { dashboardType: DashboardType.UNRESTRICTED }
      })
      expect(screen.getByRole('button', { name: 'Toggle Unrestricted' })).toHaveClass('selected')
    })

    it('does not mark Specific host or Custom as selected when UNRESTRICTED', () => {
      render(DashboardTypeSelector, {
        props: { dashboardType: DashboardType.UNRESTRICTED }
      })
      expect(screen.getByRole('button', { name: 'Toggle Specific host' })).not.toHaveClass(
        'selected'
      )
      expect(screen.getByRole('button', { name: 'Toggle Custom' })).not.toHaveClass('selected')
    })

    it('marks Custom as selected when dashboardType is CUSTOM', () => {
      render(DashboardTypeSelector, {
        props: { dashboardType: DashboardType.CUSTOM }
      })
      expect(screen.getByRole('button', { name: 'Toggle Custom' })).toHaveClass('selected')
    })

    it('marks Specific host as selected when dashboardType is SPECIFIC_HOST', () => {
      render(DashboardTypeSelector, {
        props: { dashboardType: DashboardType.SPECIFIC_HOST }
      })
      expect(screen.getByRole('button', { name: 'Toggle Specific host' })).toHaveClass('selected')
    })
  })

  describe('Events', () => {
    it('emits update:dashboardType with CUSTOM when Custom button is clicked', async () => {
      const { emitted } = render(DashboardTypeSelector, {
        props: { dashboardType: DashboardType.UNRESTRICTED }
      })
      await fireEvent.click(screen.getByRole('button', { name: 'Toggle Custom' }))
      expect(emitted()['update:dashboardType']).toEqual([[DashboardType.CUSTOM]])
    })

    it('emits update:dashboardType with SPECIFIC_HOST when Specific host is clicked', async () => {
      const { emitted } = render(DashboardTypeSelector, {
        props: { dashboardType: DashboardType.UNRESTRICTED }
      })
      await fireEvent.click(screen.getByRole('button', { name: 'Toggle Specific host' }))
      expect(emitted()['update:dashboardType']).toEqual([[DashboardType.SPECIFIC_HOST]])
    })

    it('emits update:dashboardType with UNRESTRICTED when Unrestricted is clicked', async () => {
      const { emitted } = render(DashboardTypeSelector, {
        props: { dashboardType: DashboardType.CUSTOM }
      })
      await fireEvent.click(screen.getByRole('button', { name: 'Toggle Unrestricted' }))
      expect(emitted()['update:dashboardType']).toEqual([[DashboardType.UNRESTRICTED]])
    })

    it('emits exactly one event per click', async () => {
      const { emitted } = render(DashboardTypeSelector, {
        props: { dashboardType: DashboardType.UNRESTRICTED }
      })
      await fireEvent.click(screen.getByRole('button', { name: 'Toggle Custom' }))
      expect(emitted()['update:dashboardType']).toHaveLength(1)
    })
  })
})
