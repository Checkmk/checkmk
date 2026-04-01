/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { describe, expect, it, vi } from 'vitest'
import { defineComponent } from 'vue'

import DashboardScope from '@/dashboard/components/Wizard/components/DashboardSettings/DashboardScope.vue'

vi.mock('@/dashboard/components/selectors/SelectorSingleInfo.vue', () => ({
  default: defineComponent({
    name: 'SelectorSingleInfo',
    props: {
      selectedIds: { type: Array as () => string[], default: () => [] },
      hasErrors: { type: Boolean, default: false }
    },
    emits: ['update:selectedIds'],
    template: `
      <div data-testid="selector-single-info" :data-has-errors="hasErrors">
        <button
          data-testid="trigger-update"
          @click="$emit('update:selectedIds', ['host1', 'host2'])"
        >trigger</button>
      </div>
    `
  })
}))

const renderComponent = (
  props: { selectionErrors?: string[] } = {},
  selectedIds: string[] = []
) => {
  return render(DashboardScope, {
    props: {
      ...props,
      selectedIds
    }
  })
}

describe('DashboardScope', () => {
  describe('Rendering', () => {
    it('renders the scope label text', () => {
      renderComponent()
      expect(screen.getByText('Choose which objects this dashboard applies to')).toBeInTheDocument()
    })

    it('renders the required marker', () => {
      renderComponent()
      expect(screen.getByText('(required)')).toBeInTheDocument()
    })

    it('renders SelectorSingleInfo', () => {
      renderComponent()
      expect(screen.getByTestId('selector-single-info')).toBeInTheDocument()
    })

    it('does not render validation errors when selectionErrors is empty', () => {
      renderComponent({ selectionErrors: [] })
      expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    })

    it('does not render validation errors when selectionErrors is undefined', () => {
      renderComponent()
      expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    })

    it('renders validation error messages when selectionErrors has items', () => {
      renderComponent({ selectionErrors: ['At least one object must be selected'] })
      expect(screen.getByText('At least one object must be selected')).toBeInTheDocument()
    })

    it('renders multiple validation error messages', () => {
      renderComponent({ selectionErrors: ['Error one', 'Error two'] })
      expect(screen.getByText('Error one')).toBeInTheDocument()
      expect(screen.getByText('Error two')).toBeInTheDocument()
    })
  })

  describe('SelectorSingleInfo props', () => {
    it('passes hasErrors=false to SelectorSingleInfo when selectionErrors is empty', () => {
      renderComponent({ selectionErrors: [] })
      const selector = screen.getByTestId('selector-single-info')
      expect(selector.getAttribute('data-has-errors')).toBe('false')
    })

    it('passes hasErrors=true to SelectorSingleInfo when selectionErrors has items', () => {
      renderComponent({ selectionErrors: ['Required'] })
      const selector = screen.getByTestId('selector-single-info')
      expect(selector.getAttribute('data-has-errors')).toBe('true')
    })

    it('passes hasErrors=false to SelectorSingleInfo when selectionErrors is undefined', () => {
      renderComponent()
      const selector = screen.getByTestId('selector-single-info')
      expect(selector.getAttribute('data-has-errors')).toBe('false')
    })
  })

  describe('v-model:selectedIds', () => {
    it('emits update:selectedIds when SelectorSingleInfo updates', async () => {
      const { emitted } = render(DashboardScope, {
        props: { selectedIds: [] }
      })

      await fireEvent.click(screen.getByTestId('trigger-update'))

      expect(emitted()['update:selectedIds']).toEqual([[['host1', 'host2']]])
    })

    it('renders with initial selectedIds', () => {
      renderComponent({}, ['host1', 'host2'])
      expect(screen.getByTestId('selector-single-info')).toBeInTheDocument()
    })
  })
})
