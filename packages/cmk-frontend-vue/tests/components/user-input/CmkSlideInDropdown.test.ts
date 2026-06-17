/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/vue'
import { h } from 'vue'

import { untranslated } from '@/lib/i18n'

import CmkSlideInDropdown, {
  type CmkSlideInDropdownChoice
} from '@/components/user-input/CmkSlideInDropdown'

const choices: Array<CmkSlideInDropdownChoice> = [
  { name: 'entity-1', title: untranslated('Entity One') },
  { name: 'entity-2', title: untranslated('Entity Two') }
]

afterEach(() => {
  cleanup()
})

type SlideInSlot = (props: { objectId: string | null; close: () => void }) => unknown

function renderComponent(
  props: {
    modelValue?: string | null
    choices?: Array<CmkSlideInDropdownChoice>
    allowEditingExistingElements?: boolean
    validation?: Array<string>
    label?: string
    inputHint?: string
    slideIn?: SlideInSlot
  } = {}
) {
  const { modelValue = null, choices: choicesProp = choices, slideIn, ...rest } = props
  return render(CmkSlideInDropdown, {
    props: {
      modelValue,
      'onUpdate:modelValue': () => {},
      choices: choicesProp,
      label: 'Select entity',
      newTitle: untranslated('New entity'),
      editTitle: untranslated('Edit entity'),
      ...rest
    },
    slots: {
      'slide-in': slideIn ?? (() => `slide-in body`)
    }
  })
}

test('shows no-elements text when no choices available', async () => {
  renderComponent({ choices: [] })
  await screen.findByLabelText('No options available')
})

test('uses inputHint as dropdown placeholder', async () => {
  renderComponent({ inputHint: 'Pick a parameter...' })
  await screen.findByLabelText('Pick a parameter...')
})

test('always shows create button', async () => {
  renderComponent()
  await screen.findByRole('button', { name: /Create/ })
})

test('does not show edit button when nothing is selected', () => {
  renderComponent({ modelValue: null, allowEditingExistingElements: true })
  expect(screen.queryByRole('button', { name: /Edit/ })).not.toBeInTheDocument()
})

test('shows edit button when an item is selected', async () => {
  renderComponent({ modelValue: 'entity-1', allowEditingExistingElements: true })
  expect(await screen.findByRole('button', { name: /Edit/ })).toBeVisible()
})

test('does not show edit button when allowEditingExistingElements is false', async () => {
  renderComponent({ modelValue: 'entity-1', allowEditingExistingElements: false })
  expect(screen.queryByRole('button', { name: /Edit/, hidden: true })).not.toBeInTheDocument()
})

test('does not show edit button for choice with hideEdit flag', async () => {
  renderComponent({
    modelValue: 'entity-1',
    allowEditingExistingElements: true,
    choices: [{ name: 'entity-1', title: untranslated('Entity One'), hideEdit: true }]
  })
  await waitFor(() => {
    expect(screen.queryByRole('button', { name: /Edit/, hidden: true })).not.toBeInTheDocument()
  })
})

test('opens slide-in with new title when clicking create', async () => {
  renderComponent()
  await fireEvent.click(screen.getByRole('button', { name: /Create/ }))
  await screen.findByText('New entity')
  await screen.findByText('slide-in body')
})

test('opens slide-in with edit title when clicking edit', async () => {
  renderComponent({ modelValue: 'entity-1', allowEditingExistingElements: true })
  await fireEvent.click(await screen.findByRole('button', { name: /Edit/ }))
  await screen.findByText('Edit entity')
})

test('passes a null objectId to the slide-in slot when creating', async () => {
  renderComponent({
    slideIn: ({ objectId }) => `objectId: ${objectId ?? '(new)'}`
  })
  await fireEvent.click(screen.getByRole('button', { name: /Create/ }))
  await screen.findByText('objectId: (new)')
})

test('passes the selected objectId to the slide-in slot when editing', async () => {
  renderComponent({
    modelValue: 'entity-1',
    allowEditingExistingElements: true,
    slideIn: ({ objectId }) => `objectId: ${objectId ?? '(new)'}`
  })
  await fireEvent.click(await screen.findByRole('button', { name: /Edit/ }))
  await screen.findByText('objectId: entity-1')
})

test('closes the slide-in via the close callback passed to the slot', async () => {
  renderComponent({
    slideIn: ({ close }) => h('button', { onClick: close }, 'Done')
  })
  await fireEvent.click(screen.getByRole('button', { name: /Create/ }))
  await fireEvent.click(await screen.findByRole('button', { name: 'Done' }))
  await waitFor(() => {
    expect(screen.queryByText('New entity')).not.toBeInTheDocument()
  })
})

test('closes slide-in when close button is clicked', async () => {
  renderComponent()
  await fireEvent.click(screen.getByRole('button', { name: /Create/ }))
  await screen.findByText('New entity')
  await fireEvent.click(screen.getByRole('button', { name: 'Close' }))
  await waitFor(() => {
    expect(screen.queryByText('New entity')).not.toBeInTheDocument()
  })
})

test('displays validation messages', async () => {
  renderComponent({ validation: ['This field is required'] })
  await screen.findByText('This field is required')
})

test('does not display validation messages when no validation prop', async () => {
  renderComponent()
  expect(screen.queryByText('This field is required')).not.toBeInTheDocument()
})
