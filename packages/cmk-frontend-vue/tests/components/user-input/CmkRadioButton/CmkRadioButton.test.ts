/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { defineComponent } from 'vue'

import CmkRadioButton from '@/components/user-input/CmkRadioButton/CmkRadioButton.vue'
import CmkRadioGroup from '@/components/user-input/CmkRadioButton/CmkRadioGroup.vue'

// RadioGroupItem reads its selection state from the surrounding RadioGroupRoot, so the
// button is always rendered inside a CmkRadioGroup.
const renderGroup = () =>
  render(
    defineComponent({
      components: { CmkRadioGroup, CmkRadioButton },
      template: `
        <CmkRadioGroup>
          <CmkRadioButton value="a" label="Option A" />
          <CmkRadioButton value="b" label="Option B" />
        </CmkRadioGroup>
      `
    })
  )

test('CmkRadioButton renders its label', async () => {
  renderGroup()

  await screen.findByText('Option A')
  await screen.findByText('Option B')
})

test('CmkRadioButton omits the label element when no label is given', () => {
  render(
    defineComponent({
      components: { CmkRadioGroup, CmkRadioButton },
      template: `
        <CmkRadioGroup>
          <CmkRadioButton value="a" />
        </CmkRadioGroup>
      `
    })
  )

  expect(screen.getByRole('radio')).toBeInTheDocument()
  // The label slot wraps a <label> element; without a label prop none is rendered.
  expect(document.querySelector('label')).toBeNull()
})

test('CmkRadioButton associates its label with the radio via for/id', async () => {
  renderGroup()

  const radio = screen.getByRole('radio', { name: 'Option A' })
  const label = screen.getByText('Option A').closest('label')

  expect(label).not.toBeNull()
  expect(label).toHaveAttribute('for', radio.id)
  expect(radio.id).toBeTruthy()

  // Clicking the label selects the associated radio.
  await fireEvent.click(label!)
  expect(radio).toHaveAttribute('aria-checked', 'true')
})

test('CmkRadioButton renders its label as HTML', () => {
  render(
    defineComponent({
      components: { CmkRadioGroup, CmkRadioButton },
      template: `
        <CmkRadioGroup>
          <CmkRadioButton value="a" label="<b>Bold</b>" />
        </CmkRadioGroup>
      `
    })
  )

  expect(screen.getByText('Bold').tagName).toBe('B')
})

test('CmkRadioButton renders a help tooltip from the help prop', async () => {
  render(
    defineComponent({
      components: { CmkRadioGroup, CmkRadioButton },
      template: `
        <CmkRadioGroup>
          <CmkRadioButton value="a" label="Option A" help="some help" />
        </CmkRadioGroup>
      `
    })
  )

  // The help affordance is the only non-radio button in the tree.
  const trigger = screen.getByRole('button')
  await fireEvent.click(trigger)

  // The help text renders both a tooltip and an accessible live region.
  expect(await screen.findAllByText('some help')).not.toHaveLength(0)
})

test('CmkRadioButton marks itself disabled from the disabled prop', () => {
  render(
    defineComponent({
      components: { CmkRadioGroup, CmkRadioButton },
      template: `
        <CmkRadioGroup>
          <CmkRadioButton value="a" label="Option A" />
          <CmkRadioButton value="b" label="Option B" disabled />
        </CmkRadioGroup>
      `
    })
  )

  expect(screen.getByRole('radio', { name: 'Option A' })).not.toBeDisabled()
  const disabled = screen.getByRole('radio', { name: 'Option B' })
  expect(disabled).toBeDisabled()
  expect(disabled).toHaveAttribute('data-disabled')
})
