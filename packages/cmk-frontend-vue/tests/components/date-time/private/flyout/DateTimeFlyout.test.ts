/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { afterEach, expect, test, vi } from 'vitest'
import { defineComponent } from 'vue'

import DateTimeFlyout from '@/components/date-time/private/flyout/DateTimeFlyout.vue'

afterEach(() => {
  vi.restoreAllMocks()
})

// DateTimeFlyout is presentational: it relays v-model:open / v-model:save-checked, relabels the
// Apply button, and emits apply/cancel. The save handler, model commit and close-on-apply now live
// in the owner (see useDateTimeDraft's confirm), so this host just records the emitted apply/cancel.
// The flyout is fully controlled (it never opens itself), so the host's trigger toggles `open`;
// saveChecked starts true so the button shows its "Save & apply" label by default.
const renderFlyout = (props: Record<string, unknown> = {}) =>
  render(
    defineComponent({
      components: { DateTimeFlyout },
      data: () => ({
        open: false,
        saveChecked: true,
        applyCount: 0,
        cancelCount: 0,
        boundProps: props
      }),
      template: `
        <DateTimeFlyout
          v-model:open="open"
          v-model:save-checked="saveChecked"
          :restore-focus="() => {}"
          v-bind="boundProps"
          @apply="applyCount++"
          @cancel="cancelCount++"
        >
          <template #trigger="{ aria }">
            <button type="button" v-bind="aria" @click="open = !open">Toggle</button>
          </template>
          <div>Flyout body</div>
        </DateTimeFlyout>
        <span data-testid="open">{{ open }}</span>
        <span data-testid="apply">{{ applyCount }}</span>
        <span data-testid="cancel">{{ cancelCount }}</span>
      `
    })
  )

const openState = () => screen.getByTestId('open').textContent
const applyCount = () => screen.getByTestId('apply').textContent
const cancelCount = () => screen.getByTestId('cancel').textContent

const openFlyout = async () => fireEvent.click(screen.getByRole('button', { name: 'Toggle' }))

test('footer Apply emits apply and leaves open to the owner', async () => {
  // showActions surfaces the footer without save mode. The flyout no longer closes itself on apply;
  // the owner's confirm decides that, so `open` stays put here.
  renderFlyout({ showActions: true })
  await openFlyout()

  await fireEvent.click(screen.getByRole('button', { name: 'Apply' }))

  expect(applyCount()).toBe('1')
  expect(openState()).toBe('true')
})

test('the "Save & apply" button emits the same plain apply (gating lives in the owner)', async () => {
  // saveChecked starts true, so the button is labelled "Save & apply"; clicking it still just emits
  // `apply` — the flyout knows nothing about the save handler anymore.
  renderFlyout({ saveMode: true })
  await openFlyout()

  await fireEvent.click(screen.getByRole('button', { name: 'Save & apply' }))

  expect(applyCount()).toBe('1')
})

test('footer cancel emits cancel and closes', async () => {
  renderFlyout({ showActions: true })
  await openFlyout()

  await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

  expect(cancelCount()).toBe('1')
  expect(openState()).toBe('false')
})

test('applyLabel is "Save & apply" while save mode and the checkbox are both on', async () => {
  // saveChecked starts true in the host.
  renderFlyout({ saveMode: true })
  await openFlyout()

  expect(screen.getByRole('button', { name: 'Save & apply' })).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Apply' })).not.toBeInTheDocument()
})

test('applyLabel is "Apply" when not (save mode && checked)', async () => {
  renderFlyout({ saveMode: true })
  await openFlyout()
  expect(screen.getByRole('button', { name: 'Save & apply' })).toBeInTheDocument()

  // Unchecking the save box collapses the label back to "Apply".
  await fireEvent.click(screen.getByRole('checkbox'))

  expect(screen.getByRole('button', { name: 'Apply' })).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Save & apply' })).not.toBeInTheDocument()
})

test('pendingSave announces "Saving…" but leaves Apply enabled', async () => {
  renderFlyout({ saveMode: true, pendingSave: true })
  await openFlyout()

  expect(screen.getByRole('status')).toHaveTextContent('Saving…')
  expect(screen.getByRole('button', { name: 'Save & apply' })).toBeEnabled()
})

test('"Saving…" takes precedence over the disabled reason', async () => {
  renderFlyout({
    showActions: true,
    pendingSave: true,
    applyDisabled: true,
    applyDisabledReason: 'Enter a complete date'
  })
  await openFlyout()

  expect(screen.getByRole('status')).toHaveTextContent('Saving…')
})

test('the disabled reason is announced when not saving', async () => {
  renderFlyout({
    showActions: true,
    applyDisabled: true,
    applyDisabledReason: 'Enter a complete date'
  })
  await openFlyout()

  expect(screen.getByRole('status')).toHaveTextContent('Enter a complete date')
})

test('cancel is blocked while a save is in flight', async () => {
  renderFlyout({ showActions: true, pendingSave: true })
  await openFlyout()

  await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

  expect(cancelCount()).toBe('0')
  expect(openState()).toBe('true')
})
