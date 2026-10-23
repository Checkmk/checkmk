/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import { defineComponent } from 'vue'

test('CmkCheckbox can be appended with standard props', async () => {
  render(
    defineComponent({
      components: { CmkCheckbox },
      template: `
          <CmkCheckbox role='option'/>
      `
    })
  )

  await screen.findByRole('option')
})

test('CmkCheckbox sets aria-checked', async () => {
  render(CmkCheckbox, {
    props: {
      modelValue: true
    }
  })

  screen.getByRole('checkbox', { checked: true })
})

test('the checkmark and dash icons are hidden from the accessibility tree', async () => {
  const { container, rerender } = render(CmkCheckbox, {
    props: { allowIndeterminate: true, modelValue: true }
  })

  // The state is already conveyed by aria-checked on the button; the icons are decorative
  // and would otherwise surface as unlabelled graphics to assistive tech.
  expect(container.querySelector('.cmk-checkbox__indicator')).toHaveAttribute('aria-hidden', 'true')
  expect(container.querySelector('.cmk-checkbox__indicator svg')).toHaveAttribute(
    'focusable',
    'false'
  )

  await rerender({ modelValue: 'indeterminate' })

  expect(container.querySelector('.cmk-checkbox__dash')).toBeInTheDocument()
  expect(container.querySelector('.cmk-checkbox__indicator')).toHaveAttribute('aria-hidden', 'true')
})

test('CmkCheckbox exposes the mixed state via aria-checked when indeterminate', async () => {
  render(CmkCheckbox, {
    props: {
      allowIndeterminate: true,
      modelValue: 'indeterminate'
    }
  })

  expect(screen.getByRole('checkbox')).toHaveAttribute('aria-checked', 'mixed')
})

test('CmkCheckbox transitions from indeterminate to checked on click', async () => {
  const user = userEvent.setup()
  const { emitted } = render(CmkCheckbox, {
    props: {
      allowIndeterminate: true,
      modelValue: 'indeterminate'
    }
  })

  await user.click(screen.getByRole('checkbox'))

  expect(emitted('update:modelValue')).toEqual([[true]])
})

test('CmkCheckbox toggles between checked and unchecked on click', async () => {
  const user = userEvent.setup()
  const { emitted } = render(CmkCheckbox, {
    props: {
      modelValue: false
    }
  })

  await user.click(screen.getByRole('checkbox'))

  expect(emitted('update:modelValue')).toEqual([[true]])
})

test('CmkCheckbox renders updated validation', async () => {
  const { rerender } = render(CmkCheckbox, {
    props: {
      modelValue: false,
      externalErrors: ['some old validation']
    }
  })

  await rerender({
    modelValue: false,
    externalErrors: ['some new validation']
  })

  await screen.findByText('some new validation')
})

test('slotted content renders below the label without joining the accessible name', async () => {
  render(CmkCheckbox, {
    props: { label: 'Expire on' },
    slots: { default: '<button type="button">pick a date</button>' }
  })

  // The name has to stay the label alone: consumers address checkboxes by it.
  screen.getByRole('checkbox', { name: 'Expire on' })
  screen.getByRole('button', { name: 'pick a date' })
})

test('clicking slotted content leaves the checkbox alone', async () => {
  const { emitted } = render(CmkCheckbox, {
    props: { label: 'Expire on', modelValue: false },
    slots: { default: '<button type="button">pick a date</button>' }
  })

  await userEvent.click(screen.getByRole('button', { name: 'pick a date' }))

  // A control inside the <label> would toggle the box; this one sits outside it.
  expect(emitted('update:modelValue')).toBeUndefined()
  expect(screen.getByRole('checkbox')).not.toBeChecked()
})

test('the label slot supplies the accessible name and still toggles on click', async () => {
  const { emitted } = render(CmkCheckbox, {
    props: { modelValue: false },
    slots: { label: 'Notify affected users' }
  })

  await userEvent.click(screen.getByText('Notify affected users'))

  expect(screen.getByRole('checkbox', { name: 'Notify affected users' })).toBeInTheDocument()
  expect(emitted('update:modelValue')).toEqual([[true]])
})

test('a checkbox with only an ariaLabel is still named', () => {
  render(CmkCheckbox, {
    props: { modelValue: false, ariaLabel: 'Select row' }
  })

  // A real <label> supplies the accessible name (content-based, not an aria-label
  // attribute) - satisfying tooling that flags aria-label-only controls as unlabelled,
  // and avoiding giving the name twice over to tooling that reads both.
  const checkbox = screen.getByRole<HTMLButtonElement>('checkbox', { name: 'Select row' })
  expect(checkbox.labels).toHaveLength(1)
  expect(checkbox.labels?.[0]).toHaveTextContent('Select row')
})

test('an ariaLabel still names the checkbox alongside slotted content', () => {
  render(CmkCheckbox, {
    props: { modelValue: false, ariaLabel: 'Select row' },
    slots: { default: '<span>a hint</span>' }
  })

  // The slot sits outside the label, so it neither replaces nor joins the name.
  screen.getByRole('checkbox', { name: 'Select row' })
})
