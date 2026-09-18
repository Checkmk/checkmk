/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'

afterEach(() => {
  vi.useRealTimers()
})

test('CmkAlert renders heading and text', () => {
  render(CmkAlert, { props: { heading: 'Saved', text: 'Your changes were saved.' } })
  screen.getByRole('heading', { name: 'Saved' })
  screen.getByText('Your changes were saved.')
})

test('CmkAlert announces warnings and errors as alerts', () => {
  render(CmkAlert, { props: { variant: 'warning', text: 'Check the port.' } })
  screen.getByRole('alert')
})

test('CmkAlert announces info as status', () => {
  render(CmkAlert, { props: { variant: 'info', text: 'Sync is running.' } })
  screen.getByRole('status')
})

test('CmkAlert small size offers the full text on hover', () => {
  render(CmkAlert, { props: { size: 'small', text: 'A long message that gets cut off.' } })
  screen.getByTitle('A long message that gets cut off.')
})

test('CmkAlert medium size does not repeat the text as a tooltip', () => {
  render(CmkAlert, { props: { text: 'A message that wraps freely.' } })
  expect(screen.queryByTitle('A message that wraps freely.')).toBeNull()
})

test('CmkAlert dismissible success closes via the close button', async () => {
  render(CmkAlert, { props: { variant: 'success', dismissible: true, text: 'Done.' } })
  await userEvent.click(screen.getByRole('button', { name: 'Close' }))
  expect(screen.queryByRole('status')).toBeNull()
})

test('CmkAlert with buttons offers no close button', () => {
  render(CmkAlert, {
    props: {
      variant: 'info',
      dismissible: true,
      heading: 'Confirm',
      text: 'Continue?',
      mainButton: { title: 'Confirm', onclick: () => {} }
    }
  })
  expect(screen.queryByRole('button', { name: 'Close' })).toBeNull()
})

test('CmkAlert runs the main button action', async () => {
  let confirmed = false
  render(CmkAlert, {
    props: {
      heading: 'Confirm',
      text: 'Continue?',
      mainButton: {
        title: 'Confirm',
        onclick: () => {
          confirmed = true
        }
      }
    }
  })
  await userEvent.click(screen.getByRole('button', { name: 'Confirm' }))
  expect(confirmed).toBe(true)
})

test('CmkAlert auto-dismisses after 6s when autoDismiss is true from mount', async () => {
  vi.useFakeTimers()
  render(CmkAlert, { props: { autoDismiss: true, open: true, text: 'Saved.' } })
  screen.getByRole('status')
  await vi.advanceTimersByTimeAsync(6000)
  expect(screen.queryByRole('status')).toBeNull()
})

test('CmkAlert auto-dismisses after 6s when autoDismiss is toggled on while open', async () => {
  vi.useFakeTimers()
  const { rerender } = render(CmkAlert, {
    props: { autoDismiss: false, open: true, text: 'Saved.' }
  })
  screen.getByRole('status')
  await rerender({ autoDismiss: true, open: true, text: 'Saved.' })
  await vi.advanceTimersByTimeAsync(6000)
  expect(screen.queryByRole('status')).toBeNull()
})

test('CmkAlert stays open when autoDismiss is false', async () => {
  vi.useFakeTimers()
  render(CmkAlert, { props: { autoDismiss: false, open: true, text: 'Saved.' } })
  await vi.advanceTimersByTimeAsync(10000)
  screen.getByRole('status')
})
