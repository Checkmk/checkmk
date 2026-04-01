/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import { describe, expect, it, vi } from 'vitest'

import DashboardSelector from '@/dashboard/components/DashboardMenuHeader/DashboardSelector.vue'
import type { SelectedDashboard } from '@/dashboard/components/DashboardMenuHeader/types'
import type { DashboardMetadata } from '@/dashboard/types/dashboard'
import { DashboardOwnerType } from '@/dashboard/types/dashboard'
import { dashboardAPI } from '@/dashboard/utils.ts'

vi.mock('@/dashboard/utils.ts', () => ({
  dashboardAPI: {
    listDashboardMetadata: vi.fn().mockResolvedValue([
      {
        name: 'custom-b',
        owner: 'admin',
        is_built_in: false,
        display: { title: 'Custom B', hide_in_drop_down_menus: false, sort_index: 0 }
      },
      {
        name: 'custom-a',
        owner: 'admin',
        is_built_in: false,
        display: { title: 'Custom A', hide_in_drop_down_menus: false, sort_index: 0 }
      },
      {
        name: 'builtin-b',
        owner: '',
        is_built_in: true,
        display: { title: 'Built-in B', hide_in_drop_down_menus: false, sort_index: 2 }
      },
      {
        name: 'builtin-a',
        owner: '',
        is_built_in: true,
        display: { title: 'Built-in A', hide_in_drop_down_menus: false, sort_index: 1 }
      },
      {
        name: 'hidden',
        owner: 'admin',
        is_built_in: false,
        display: { title: 'Hidden', hide_in_drop_down_menus: true, sort_index: 0 }
      }
    ] as DashboardMetadata[])
  }
}))

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
      vi.mocked(dashboardAPI.listDashboardMetadata).mockResolvedValueOnce([
        {
          name: 'builtin-alpha',
          owner: '',
          is_built_in: true,
          display: { title: 'Alpha', hide_in_drop_down_menus: false, sort_index: 20 }
        },
        {
          name: 'builtin-zebra',
          owner: '',
          is_built_in: true,
          display: { title: 'Zebra', hide_in_drop_down_menus: false, sort_index: 10 }
        }
      ] as DashboardMetadata[])

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

      expect(screen.getByTitle('Custom A')).toHaveClass('active')
      expect(screen.getByTitle('Custom B')).not.toHaveClass('active')
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
