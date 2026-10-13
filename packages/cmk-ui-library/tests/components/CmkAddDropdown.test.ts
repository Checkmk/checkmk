/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import CmkAddDropdown from 'cmk-ui-library/components/CmkDropdown/CmkAddDropdown.vue'
import type { Suggestions } from 'cmk-ui-library/components/CmkSuggestions'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { defineComponent, h, shallowRef } from 'vue'

const OPTIONS: Suggestions = {
  type: 'fixed',
  suggestions: [
    { name: 'metrics_backend', title: untranslated('Metrics backend') },
    { name: 'cmk_rrd', title: untranslated('CMK RRD') }
  ]
}

function mountAddDropdown(
  onSelect: (value: string) => void = () => {},
  props: { floating?: boolean } = {}
) {
  return render(
    defineComponent({
      render() {
        return h(CmkAddDropdown, {
          options: OPTIONS,
          label: untranslated('Add scope'),
          onSelect,
          ...props
        })
      }
    })
  )
}

test('shows the label as button text with a plus icon', () => {
  mountAddDropdown()

  const button = screen.getByRole('combobox', { name: 'Add scope' })
  expect(button).toHaveTextContent('Add scope')
  expect(button.querySelector('img')).not.toBeNull()
})

test('selecting an option emits select and keeps the button unselected', async () => {
  const onSelect = vi.fn()
  mountAddDropdown(onSelect)

  await fireEvent.click(screen.getByRole('combobox', { name: 'Add scope' }))
  await fireEvent.click(await screen.findByText('CMK RRD'))

  expect(onSelect).toHaveBeenCalledWith('cmk_rrd')
  await waitFor(() => {
    expect(screen.getByRole('combobox', { name: 'Add scope' })).toHaveTextContent('Add scope')
  })
})

test('with floating, the menu teleports out of the dropdown and selection still emits', async () => {
  const onSelect = vi.fn()
  mountAddDropdown(onSelect, { floating: true })

  const button = screen.getByRole('combobox', { name: 'Add scope' })
  await fireEvent.click(button)

  const option = await screen.findByText('CMK RRD')
  // The floating menu is portalled out of the `.cmk-dropdown` control, not an inline child.
  expect(button.closest('.cmk-dropdown')?.contains(option)).toBe(false)

  await fireEvent.click(option)
  expect(onSelect).toHaveBeenCalledWith('cmk_rrd')
})

test('a second pick of the same option emits again', async () => {
  const onSelect = vi.fn()
  mountAddDropdown(onSelect)

  for (const _ of [1, 2]) {
    await fireEvent.click(screen.getByRole('combobox', { name: 'Add scope' }))
    await fireEvent.click(await screen.findByText('CMK RRD'))
    await waitFor(() => {
      expect(screen.getByRole('combobox', { name: 'Add scope' })).toHaveTextContent('Add scope')
    })
  }

  expect(onSelect).toHaveBeenCalledTimes(2)
  expect(onSelect).toHaveBeenNthCalledWith(2, 'cmk_rrd')
})

test('a component id lands on the button, so a label outside can point at it', () => {
  render(
    defineComponent({
      render() {
        return [
          h('label', { for: 'add-id' }, 'Host filter'),
          h(CmkAddDropdown, {
            options: OPTIONS,
            label: untranslated('Add host filter'),
            componentId: 'add-id'
          })
        ]
      }
    })
  )

  // The button keeps naming itself: an aria-label wins over the label pointing at it.
  expect(screen.getByLabelText('Host filter')).toBe(
    screen.getByRole('combobox', { name: 'Add host filter' })
  )
})

test('exposes focus, putting keyboard focus on the button', () => {
  const dropdown = shallowRef<{ focus: () => void } | null>(null)
  render(
    defineComponent({
      render() {
        return h(CmkAddDropdown, {
          ref: (el) => {
            dropdown.value = el as { focus: () => void } | null
          },
          options: OPTIONS,
          label: untranslated('Add scope')
        })
      }
    })
  )

  dropdown.value!.focus()

  expect(screen.getByRole('combobox', { name: 'Add scope' })).toHaveFocus()
})
