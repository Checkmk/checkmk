/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { afterEach, expect, test, vi } from 'vitest'
import { defineComponent, ref } from 'vue'

import InlineEditPill from '@/metric-backend/InlineEditPill.vue'

afterEach(() => {
  vi.useRealTimers()
})

const markers = { scopeMarkerAttr: 'data-af-scope', itemMarkerAttr: 'data-af-item' }

function renderCollapsed(props: Record<string, unknown> = {}) {
  return render(InlineEditPill, {
    props: { editAriaLabel: 'Edit pill', ...markers, ...props },
    slots: { 'read-only': '<span>summary</span>' }
  })
}

function renderEditing(props: Record<string, unknown> = {}) {
  return render(InlineEditPill, {
    props: { editing: true, removable: true, removeLabel: 'Remove', ...markers, ...props },
    slots: { edit: '<span>edit content</span>' }
  })
}

// Drives `editing` like the real parent (collapses on done) so focus-return and veto run end to end.
function mountHost(canLeave?: (reason: string) => boolean) {
  const editing = ref(true)
  const done = vi.fn((_reason: string) => {
    editing.value = false
  })
  const host = defineComponent({
    components: { InlineEditPill },
    setup() {
      return { editing, done, canLeave }
    },
    template: `
      <InlineEditPill :editing="editing" :can-leave="canLeave" edit-aria-label="Edit"
        scope-marker-attr="data-af-scope" item-marker-attr="data-af-item" @done="done">
        <template #edit><input aria-label="field" /></template>
        <template #read-only><span>summary</span></template>
      </InlineEditPill>
    `
  })
  return { ...render(host), editing, done }
}

test('the collapsed pill shows the read-only slot, carries the item marker, and opens on click', async () => {
  const { container, emitted } = renderCollapsed()

  const button = screen.getByRole('button', { name: 'Edit pill' })
  expect(button).toHaveTextContent('summary')
  expect(container.querySelector('.metric-backend-inline-edit-pill__closed')).toHaveAttribute(
    'data-af-item'
  )

  await userEvent.click(button)
  expect(emitted('edit')).toHaveLength(1)
})

test('Enter and Space open the pill, Delete removes it', async () => {
  const { container, emitted } = renderCollapsed()
  const closed = container.querySelector<HTMLElement>('.metric-backend-inline-edit-pill__closed')!
  closed.focus()

  await userEvent.keyboard('{Enter}')
  await userEvent.keyboard(' ')
  expect(emitted('edit')).toHaveLength(2)

  await userEvent.keyboard('{Delete}')
  expect(emitted('remove')).toHaveLength(1)
})

test('tabFocusable controls whether the collapsed pill is tabbable', () => {
  expect(
    renderCollapsed().container.querySelector('.metric-backend-inline-edit-pill__closed')
  ).toHaveAttribute('tabindex', '0')
  expect(
    renderCollapsed({ tabFocusable: false }).container.querySelector(
      '.metric-backend-inline-edit-pill__closed'
    )
  ).toHaveAttribute('tabindex', '-1')
})

test('the close button appears only when removable and emits remove', async () => {
  renderCollapsed({ removeLabel: 'Remove' })
  expect(screen.queryByRole('button', { name: 'Remove' })).toBeNull()

  const { emitted } = renderCollapsed({ removable: true, removeLabel: 'Remove' })
  await userEvent.click(screen.getByRole('button', { name: 'Remove' }))
  expect(emitted('remove')).toHaveLength(1)
})

test('the edit pane renders the edit slot and exposes the focus-nav markers, with configurable names', () => {
  const { container } = renderEditing()
  expect(screen.getByText('edit content')).toBeVisible()
  expect(container.querySelector('[data-af-scope]')).not.toBeNull()
  expect(screen.getByRole('button', { name: 'Remove' })).toHaveAttribute('data-af-item')

  const custom = renderEditing({ scopeMarkerAttr: 'data-x-scope', itemMarkerAttr: 'data-x-item' })
  expect(custom.container.querySelector('[data-x-scope]')).not.toBeNull()
  expect(custom.container.querySelector('[data-af-scope]')).toBeNull()
})

test('Escape commits and returns focus to the collapsed pill', async () => {
  const { container, done } = mountHost()
  screen.getByLabelText('field').focus()

  await userEvent.keyboard('{Escape}')

  expect(done).toHaveBeenCalledWith('escape')
  await waitFor(() =>
    expect(document.activeElement).toBe(
      container.querySelector('.metric-backend-inline-edit-pill__closed')
    )
  )
})

test('clicking outside commits with the outside reason', () => {
  vi.useFakeTimers()
  const { done } = mountHost()

  vi.advanceTimersByTime(0) // arm the outside-click handler
  document.body.dispatchEvent(new MouseEvent('click', { bubbles: true }))

  expect(done).toHaveBeenCalledWith('outside')
})

test('a vetoing canLeave keeps the pill in edit mode', async () => {
  const { done, editing } = mountHost(() => false)
  screen.getByLabelText('field').focus()

  await userEvent.keyboard('{Escape}')

  expect(done).not.toHaveBeenCalled()
  expect(editing.value).toBe(true)
})
