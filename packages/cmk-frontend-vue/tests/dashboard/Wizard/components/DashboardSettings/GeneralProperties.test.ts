/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { flushPromises } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { defineComponent, nextTick } from 'vue'

import GeneralProperties from '@/dashboard/components/Wizard/components/DashboardSettings/GeneralProperties.vue'
import * as utils from '@/dashboard/components/Wizard/components/DashboardSettings/utils'

vi.mock('@/lib/useDebounce', () => ({
  useDebounceFn: (fn: (...args: unknown[]) => unknown) => fn
}))

vi.mock('@/dashboard/components/Wizard/components/DashboardSettings/utils', () => ({
  toSnakeCase: (str: string) => str.toLowerCase().replace(/\s+/g, '_'),
  isIdInUse: vi.fn().mockResolvedValue(false),
  generateUniqueId: vi.fn().mockResolvedValue('my_dashboard_1')
}))

vi.mock('@/dashboard/components/Wizard/components/IconSelector/IconSelector.vue', () => ({
  default: defineComponent({
    name: 'IconSelector',
    props: {
      selectedIcon: { type: String as () => string | null, default: null },
      selectEmblems: { type: Boolean, default: false }
    },
    emits: ['update:selectedIcon'],
    template: '<div data-testid="icon-selector" />'
  })
}))

const DEFAULT_PROPS = {
  nameValidationErrors: [] as string[],
  uniqueIdValidationErrors: [] as string[],
  loggedInUser: 'admin'
}

const renderComponent = (
  props: Partial<typeof DEFAULT_PROPS> & {
    originalDashboardId?: string
  } = {},
  modelValues: {
    name?: string
    createUniqueId?: boolean
    uniqueId?: string
    addFilterSuffix?: boolean | undefined
    dashboardIcon?: string | null
    dashboardEmblem?: string | null
  } = {}
) => {
  return render(GeneralProperties, {
    props: {
      ...DEFAULT_PROPS,
      ...props,
      name: modelValues.name ?? 'My Dashboard',
      createUniqueId: modelValues.createUniqueId ?? true,
      uniqueId: modelValues.uniqueId ?? 'my_dashboard',
      ...(modelValues.addFilterSuffix !== undefined
        ? { addFilterSuffix: modelValues.addFilterSuffix }
        : {}),
      dashboardIcon: modelValues.dashboardIcon ?? null,
      dashboardEmblem: modelValues.dashboardEmblem ?? null
    }
  })
}

describe('GeneralProperties', () => {
  describe('Rendering', () => {
    it('renders the "Name" field description', () => {
      renderComponent()
      expect(screen.getByText('Name')).toBeInTheDocument()
    })

    it('renders the "Unique ID" field description', () => {
      renderComponent()
      expect(screen.getByText('Unique ID')).toBeInTheDocument()
    })

    it('renders the "Dashboard icon" field description', () => {
      renderComponent()
      expect(screen.getByText('Dashboard icon')).toBeInTheDocument()
    })

    it('renders the name input with the provided value', () => {
      renderComponent({}, { name: 'Test Dashboard' })
      expect(screen.getByDisplayValue('Test Dashboard')).toBeInTheDocument()
    })

    it('renders the name input placeholder', () => {
      renderComponent()
      expect(screen.getByPlaceholderText('Enter name')).toBeInTheDocument()
    })

    it('renders the "Automatically create unique ID" checkbox', () => {
      renderComponent()
      expect(
        screen.getByRole('checkbox', { name: /Automatically create unique ID/ })
      ).toBeInTheDocument()
    })

    it('shows unique ID suffix in checkbox label when createUniqueId is true', () => {
      renderComponent({}, { createUniqueId: true, uniqueId: 'my_dashboard' })
      expect(
        screen.getByRole('checkbox', { name: /Automatically create unique ID: my_dashboard/ })
      ).toBeInTheDocument()
    })

    it('does not show unique ID input when createUniqueId is true', () => {
      renderComponent({}, { createUniqueId: true, uniqueId: 'my_dashboard' })
      expect(screen.queryByPlaceholderText('Add unique ID')).not.toBeInTheDocument()
    })

    it('shows the unique ID input when createUniqueId is false', () => {
      renderComponent({}, { createUniqueId: false, uniqueId: 'my_dashboard' })
      expect(screen.getByPlaceholderText('Add unique ID')).toBeInTheDocument()
    })

    it('renders the unique ID input with the current value when createUniqueId is false', () => {
      renderComponent({}, { createUniqueId: false, uniqueId: 'custom_id' })
      expect(screen.getByDisplayValue('custom_id')).toBeInTheDocument()
    })

    it('does not render the "Add filter as suffix" checkbox when addFilterSuffix is undefined', () => {
      renderComponent({}, { addFilterSuffix: undefined })
      expect(screen.queryByText('Add filter as suffix')).not.toBeInTheDocument()
    })

    it('renders the "Add filter as suffix" checkbox when addFilterSuffix is defined', () => {
      renderComponent({}, { addFilterSuffix: false })
      expect(screen.getByText('Add filter as suffix')).toBeInTheDocument()
    })

    it('renders two icon selectors', () => {
      renderComponent()
      expect(screen.getAllByTestId('icon-selector')).toHaveLength(2)
    })
  })

  describe('Validation errors', () => {
    it('renders name validation error messages', () => {
      renderComponent({ nameValidationErrors: ['Name is required'] })
      expect(screen.getByText('Name is required')).toBeInTheDocument()
    })

    it('renders unique ID validation error messages when createUniqueId is false', () => {
      renderComponent(
        { uniqueIdValidationErrors: ['ID already in use'] },
        { createUniqueId: false }
      )
      expect(screen.getByText('ID already in use')).toBeInTheDocument()
    })

    it('unchecks createUniqueId checkbox when uniqueIdValidationErrors are set', async () => {
      const { rerender } = renderComponent(
        { uniqueIdValidationErrors: [] },
        { createUniqueId: true }
      )

      await rerender({
        ...DEFAULT_PROPS,
        name: 'My Dashboard',
        createUniqueId: true,
        uniqueId: 'my_dashboard',
        uniqueIdValidationErrors: ['Unique ID already in use']
      })
      await nextTick()

      expect(
        screen.getByRole('checkbox', { name: /Automatically create unique ID/ })
      ).not.toBeChecked()
    })
  })

  describe('Events', () => {
    it('emits update:name when the name input changes', async () => {
      const { emitted } = renderComponent()
      const input = screen.getByPlaceholderText('Enter name')
      await fireEvent.update(input, 'New Dashboard')
      expect(emitted()['update:name']).toBeDefined()
    })

    it('emits update:createUniqueId when the checkbox is toggled', async () => {
      const { emitted } = renderComponent({}, { createUniqueId: true })
      const checkbox = screen.getByRole('checkbox', { name: /Automatically create unique ID/ })
      await fireEvent.click(checkbox)
      expect(emitted()['update:createUniqueId']).toBeDefined()
    })

    it('emits update:uniqueId when the unique ID input changes', async () => {
      const { emitted } = renderComponent({}, { createUniqueId: false, uniqueId: 'old_id' })
      const input = screen.getByPlaceholderText('Add unique ID')
      await fireEvent.update(input, 'new_id')
      expect(emitted()['update:uniqueId']).toBeDefined()
    })
  })

  describe('Unique ID auto-generation', () => {
    it('generates unique ID from name when createUniqueId is true', async () => {
      // Use a name that produces a different uniqueId than the default '' to ensure the emit fires
      const { emitted } = renderComponent(
        {},
        { createUniqueId: true, name: 'New Dashboard', uniqueId: '' }
      )
      await flushPromises()
      await nextTick()
      const updates = emitted()['update:uniqueId']
      expect(updates).toBeDefined()
    })

    it('does not auto-generate unique ID when createUniqueId is false', async () => {
      const { emitted } = renderComponent({}, { createUniqueId: false, name: 'My Dashboard' })
      await flushPromises()
      await nextTick()
      expect(emitted()['update:uniqueId']).toBeUndefined()
    })

    it('forwards originalDashboardId to isIdInUse during auto-generation', async () => {
      const isIdInUseMock = vi.mocked(utils.isIdInUse)
      isIdInUseMock.mockClear()

      renderComponent(
        { originalDashboardId: 'original_id' },
        { createUniqueId: true, name: 'My Dashboard', uniqueId: '' }
      )
      await flushPromises()

      expect(isIdInUseMock).toHaveBeenCalledWith('admin', 'my_dashboard', 'original_id')
    })

    it('forwards originalDashboardId to generateUniqueId when the base ID is in use', async () => {
      const isIdInUseMock = vi.mocked(utils.isIdInUse)
      const generateUniqueIdMock = vi.mocked(utils.generateUniqueId)
      isIdInUseMock.mockResolvedValueOnce(true)
      generateUniqueIdMock.mockClear()

      renderComponent(
        { originalDashboardId: 'original_id' },
        { createUniqueId: true, name: 'My Dashboard', uniqueId: '' }
      )
      await flushPromises()

      expect(generateUniqueIdMock).toHaveBeenCalledWith('admin', 'my_dashboard', 'original_id')
    })

    it('uses the base ID directly when it is not in use (clone scenario)', async () => {
      const isIdInUseMock = vi.mocked(utils.isIdInUse)
      isIdInUseMock.mockResolvedValueOnce(false)

      const { emitted } = renderComponent(
        { originalDashboardId: 'original_id' },
        { createUniqueId: true, name: 'My Dashboard', uniqueId: '' }
      )
      await flushPromises()
      await nextTick()

      const updates = emitted()['update:uniqueId'] as string[][]
      expect(updates).toBeDefined()
      expect(updates[updates.length - 1]![0]).toBe('my_dashboard')
    })

    it('passes undefined to isIdInUse when originalDashboardId is not provided', async () => {
      const isIdInUseMock = vi.mocked(utils.isIdInUse)
      isIdInUseMock.mockClear()

      renderComponent({}, { createUniqueId: true, name: 'My Dashboard', uniqueId: '' })
      await flushPromises()

      expect(isIdInUseMock).toHaveBeenCalledWith('admin', 'my_dashboard', undefined)
    })
  })
})
