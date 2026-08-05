/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'

import CmkButton from '@/components/CmkButton'

test('CmkButton renders no icon without an icon prop', () => {
  render(CmkButton)
  expect(screen.queryByRole('img')).not.toBeInTheDocument()
})

test('CmkButton renders the icon before its content by default', () => {
  render(CmkButton, { props: { icon: { name: 'save' } }, slots: { default: 'Save' } })
  const button = screen.getByRole('button')
  expect(button.firstElementChild).toBe(screen.getByRole('img'))
})

test('CmkButton renders the icon after its content on the right side', () => {
  render(CmkButton, {
    props: { icon: { name: 'continue', side: 'right' } },
    slots: { default: 'Next' }
  })
  const button = screen.getByRole('button')
  expect(button.lastElementChild).toBe(screen.getByRole('img'))
})

test('CmkButton does not pulse while no action runs', () => {
  render(CmkButton)
  const button = screen.getByRole('button')
  expect(button).not.toHaveClass('cmk-button--running')
  expect(button).not.toHaveAttribute('aria-busy', 'true')
})

test('CmkButton pulses while the action it triggers runs', () => {
  render(CmkButton, { props: { running: true } })
  const button = screen.getByRole('button')
  expect(button).toHaveClass('cmk-button--running')
  expect(button).toHaveAttribute('aria-busy', 'true')
})

test('CmkButton refuses a second click while the action it triggers runs', async () => {
  const onClick = vi.fn()
  render(CmkButton, { props: { running: true, onClick }, slots: { default: 'Reschedule' } })

  await userEvent.click(screen.getByRole('button'))

  expect(screen.getByRole('button')).toBeDisabled()
  expect(onClick).not.toHaveBeenCalled()
})

test('CmkButton does not follow a link while the action it triggers runs', () => {
  const { container } = render(CmkButton, {
    props: { running: true, href: 'https://example.com/reschedule' },
    slots: { default: 'Reschedule' }
  })

  expect(container.querySelector('a')).not.toHaveAttribute('href')
})
