/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
import { describe, expect, it } from 'vitest'

import DashboardSelector from '@/dashboard/components/DashboardMenuHeader/DashboardSelector.vue'
import type { SelectedDashboard } from '@/dashboard/components/DashboardMenuHeader/types'
import type { DashboardMetadata } from '@/dashboard/types/dashboard'
import { DashboardOwnerType } from '@/dashboard/types/dashboard'

import { dashboardMetadata, dashboardMetadataListHandler } from '@tests/dashboard/apiHandlers'

function listed(
  name: string,
  title: string,
  owner: string | null,
  display: Partial<DashboardMetadata['display']> = {}
): DashboardMetadata {
  const metadata = dashboardMetadata(name, title, owner)
  return { ...metadata, display: { ...metadata.display, ...display } }
}

const server = useMswServer(
  dashboardMetadataListHandler(
    [
      listed('custom-b', 'Custom B', 'admin'),
      listed('custom-a', 'Custom A', 'admin'),
      listed('builtin-b', 'Built-in B', null, { sort_index: 2 }),
      listed('builtin-a', 'Built-in A', null, { sort_index: 1 }),
      listed('hidden', 'Hidden', 'admin', { hide_in_drop_down_menus: true })
    ],
    { allOwners: true }
  )
)

function renderSelector(
  props: Partial<{
    selectedDashboard: SelectedDashboard | null
    disabled: boolean
  }> = {}
) {
  return render(DashboardSelector, {
    props: {
      selectedDashboard: null,
      disabled: false,
      ...props
    }
  })
}

describe('DashboardSelector', () => {
  describe('rendering', () => {
    it('renders with placeholder when no dashboard is selected', () => {
      renderSelector()
      const input = screen.getByPlaceholderText('Select dashboard')
      expect(input).toBeInTheDocument()
    })

    it('renders with selected dashboard title as placeholder', () => {
      renderSelector({
        selectedDashboard: {
          name: 'test',
          owner: 'admin',
          title: 'My Dashboard',
          type: DashboardOwnerType.CUSTOM
        }
      })
      const input = screen.getByPlaceholderText('My Dashboard')
      expect(input).toBeInTheDocument()
    })

    it('applies disabled styling when disabled', () => {
      renderSelector({ disabled: true })
      const input = screen.getByRole('textbox')
      expect(input).toBeDisabled()
    })
  })

  describe('dropdown behavior', () => {
    it('opens dropdown and fetches dashboards on focus', async () => {
      renderSelector()
      const input = screen.getByRole('textbox')
      await fireEvent.focus(input)

      await waitFor(() => {
        expect(screen.getByText('Custom dashboards')).toBeInTheDocument()
      })
    })

    it('filters out hidden dashboards', async () => {
      renderSelector()
      const input = screen.getByRole('textbox')
      await fireEvent.focus(input)

      await waitFor(() => {
        expect(screen.getByText('Custom A')).toBeInTheDocument()
      })
      expect(screen.queryByText('Hidden')).not.toBeInTheDocument()
    })

    it('groups dashboards into custom and built-in sections', async () => {
      renderSelector()
      await fireEvent.focus(screen.getByRole('textbox'))

      await waitFor(() => {
        expect(screen.getByText('Custom dashboards')).toBeInTheDocument()
        expect(screen.getByText('Built-in dashboards')).toBeInTheDocument()
      })
    })

    it('sorts custom dashboards alphabetically', async () => {
      renderSelector()
      await fireEvent.focus(screen.getByRole('textbox'))

      await waitFor(() => {
        expect(screen.getByText('Custom A')).toBeInTheDocument()
      })

      const customItems = screen.getAllByTitle(/Custom/)
      expect(customItems[0]).toHaveTextContent('Custom A')
      expect(customItems[1]).toHaveTextContent('Custom B')
    })

    it('sorts built-in dashboards by sort_index', async () => {
      server.use(
        dashboardMetadataListHandler(
          [
            listed('builtin-alpha', 'Alpha', null, { sort_index: 20 }),
            listed('builtin-zebra', 'Zebra', null, { sort_index: 10 })
          ],
          { allOwners: true }
        )
      )

      renderSelector()
      await fireEvent.focus(screen.getByRole('textbox'))

      await waitFor(() => {
        expect(screen.getByText('Zebra')).toBeInTheDocument()
      })

      const builtInItems = screen.getAllByTitle(/Alpha|Zebra/)
      expect(builtInItems[0]).toHaveTextContent('Zebra')
      expect(builtInItems[1]).toHaveTextContent('Alpha')
    })

    it('highlights the active dashboard in the dropdown', async () => {
      renderSelector({
        selectedDashboard: {
          name: 'custom-a',
          owner: 'admin',
          title: 'Custom A',
          type: DashboardOwnerType.CUSTOM
        }
      })
      await fireEvent.focus(screen.getByRole('textbox'))

      await waitFor(() => {
        expect(screen.getByText('Custom A')).toBeInTheDocument()
      })

      expect(screen.getByText('Custom A')).toHaveClass('active')
      expect(screen.getByText('Custom B')).not.toHaveClass('active')
    })

    it('closes dropdown on blur', async () => {
      renderSelector()
      const input = screen.getByRole('textbox')
      await fireEvent.focus(input)

      await waitFor(() => {
        expect(screen.getByText('Custom dashboards')).toBeInTheDocument()
      })

      await fireEvent.focusOut(input)

      await waitFor(() => {
        expect(screen.queryByText('Custom dashboards')).not.toBeInTheDocument()
      })
    })
  })

  describe('filtering', () => {
    it('filters dashboards by text input', async () => {
      renderSelector()
      const input = screen.getByRole('textbox')
      await fireEvent.focus(input)

      await waitFor(() => {
        expect(screen.getByText('Custom A')).toBeInTheDocument()
      })

      await fireEvent.update(input, 'Custom A')
      expect(screen.getByText('Custom A')).toBeInTheDocument()
      expect(screen.queryByText('Custom B')).not.toBeInTheDocument()
    })

    it('shows "No dashboards found" when filter matches nothing', async () => {
      renderSelector()
      const input = screen.getByRole('textbox')
      await fireEvent.focus(input)

      await waitFor(() => {
        expect(screen.getByText('Custom A')).toBeInTheDocument()
      })

      await fireEvent.update(input, 'zzzznonexistent')
      expect(screen.getByText('No dashboards found')).toBeInTheDocument()
    })
  })

  describe('selection', () => {
    it('emits dashboard-change when a dashboard is clicked', async () => {
      const { emitted } = renderSelector()
      const input = screen.getByRole('textbox')
      await fireEvent.focus(input)

      await waitFor(() => {
        expect(screen.getByText('Custom A')).toBeInTheDocument()
      })

      await fireEvent.click(screen.getByText('Custom A'))
      expect(emitted()['dashboard-change']).toHaveLength(1)
      expect(emitted()['dashboard-change']).toMatchObject([
        [expect.objectContaining({ name: 'custom-a' })]
      ])
    })
  })
})
