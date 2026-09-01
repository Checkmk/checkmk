/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen } from '@testing-library/vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { defineComponent } from 'vue'

const submitHandler = vi.fn((e) => e.preventDefault())

beforeEach(() => {
  document.addEventListener('submit', submitHandler)
})

afterEach(() => {
  submitHandler.mockClear()
  document.removeEventListener('submit', submitHandler)
})

test('CmkButton does not submit form without click callback', async () => {
  const testComponent = defineComponent({
    components: { CmkButton },
    template: `
      <form>
        <CmkButton />
      </form>
    `
  })
  render(testComponent)
  const button = screen.getByRole('button')
  await fireEvent.click(button)
  expect(submitHandler).not.toHaveBeenCalled()
})

test('CmkButton does not submit form with click callback', async () => {
  let clicked: boolean = false
  const testComponent = defineComponent({
    components: { CmkButton },
    setup() {
      const onclick = () => {
        clicked = true
      }
      return { onclick }
    },
    template: `
      <form>
        <CmkButton @click="onclick" />
      </form>
    `
  })
  render(testComponent)
  const button = screen.getByRole('button')
  await fireEvent.click(button)
  expect(clicked).toBe(true)
  expect(submitHandler).not.toHaveBeenCalled()
})

test('CmkButton defaults to medium size', () => {
  render(CmkButton)
  expect(screen.getByRole('button')).toHaveClass('cmk-button--size-medium')
})

test('CmkButton applies small size class', () => {
  render(CmkButton, { props: { size: 'small' } })
  expect(screen.getByRole('button')).toHaveClass('cmk-button--size-small')
})

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

test('CmkButton disables natively without a reason', () => {
  render(CmkButton, { props: { disabled: true }, slots: { default: 'Save' } })
  const button = screen.getByRole('button')
  expect(button).toBeDisabled()
  expect(button).toHaveAttribute('title', '')
})

test('CmkButton keeps a blocked button hoverable and titles it with the reason', () => {
  render(CmkButton, {
    props: { disabled: true, disabledReason: untranslated('Pick a metric first') },
    slots: { default: 'Save' }
  })
  const button = screen.getByRole('button')
  expect(button).toBeEnabled()
  expect(button).toHaveAttribute('aria-disabled', 'true')
  expect(button).toHaveAttribute('title', 'Pick a metric first')
})

test('CmkButton refuses the click of a blocked button', async () => {
  const onClick = vi.fn()
  render(CmkButton, {
    props: { disabled: true, disabledReason: untranslated('Pick a metric first'), onClick },
    slots: { default: 'Save' }
  })

  await userEvent.click(screen.getByRole('button'))

  expect(onClick).not.toHaveBeenCalled()
})

test('CmkButton ignores a reason while the action is available', () => {
  render(CmkButton, {
    props: { disabledReason: untranslated('Pick a metric first'), title: 'Save the graph' },
    slots: { default: 'Save' }
  })
  expect(screen.getByRole('button')).toHaveAttribute('title', 'Save the graph')
})
