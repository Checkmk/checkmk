/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen, waitFor, waitForElementToBeRemoved } from '@testing-library/vue'
import FormAutocompleter from 'cmk-ui-library/components/FormAutocompleter/FormAutocompleter.vue'
import { useMswServer } from 'cmk-ui-library/vitest.msw'
import { HttpResponse, delay, http } from 'msw'

const CHOICES = [
  { id: 'os:windows', value: 'OS Windows' },
  { id: 'os:linux', value: 'OS Linux' }
]

useMswServer(
  http.post('*/api/internal/objects/autocomplete/*', async ({ request }) => {
    const { value } = (await request.json()) as { value: string }
    await delay(100)
    return HttpResponse.json({ choices: CHOICES.filter(({ id }) => id.includes(value)) })
  })
)

describe('FormAutocompleter', () => {
  test('should be rendered with placeholder', async () => {
    render(FormAutocompleter, {
      props: {
        placeholder: 'Search...',
        size: 7,
        id: 'test',
        label: 'Some label'
      }
    })
    const autocompleter = screen.getByRole('combobox', { name: 'Some label' })

    expect(autocompleter.textContent).toBe('Search...')
  })

  test('shoud emit entered item on pressing enter key on input without selecting any item from dropdown list', async () => {
    let selectedValue: string | null = ''
    render(FormAutocompleter, {
      props: {
        placeholder: 'Search...',
        autocompleter: { data: { ident: '', params: {} }, fetch_method: 'rest_autocomplete' },
        size: 7,
        id: 'test',
        'onUpdate:modelValue': (option: string | null) => {
          selectedValue = option
        }
      }
    })

    const dropdown = screen.getByRole('combobox')
    await userEvent.click(dropdown)
    const input = screen.getByRole('textbox')
    await fireEvent.update(input, 'os:windows')
    // TODO: we probably should switch to user-event, see
    // https://testing-library.com/docs/dom-testing-library/api-events/

    await waitFor(() => {
      expect(screen.getByRole('option', { name: 'OS Windows' })).toBeInTheDocument()
    })

    await fireEvent.keyDown(input, { key: 'Enter' })

    expect(selectedValue).toBe('os:windows')
  })

  test('on focus should open dropdown list with items', async () => {
    render(FormAutocompleter, {
      props: {
        placeholder: 'Add some labels',
        autocompleter: { data: { ident: '', params: {} }, fetch_method: 'rest_autocomplete' },
        size: 7,
        id: 'test'
      }
    })

    const dropdown = screen.getByRole('combobox')
    await userEvent.click(dropdown)
    const input = screen.getByRole('textbox')
    await fireEvent.focus(input)

    await waitFor(() => {
      expect(screen.getByRole('option', { name: 'OS Windows' })).toBeInTheDocument()
      expect(screen.getByRole('option', { name: 'OS Linux' })).toBeInTheDocument()
    })
  })

  test('on input should open dropdown list with items', async () => {
    render(FormAutocompleter, {
      props: {
        placeholder: 'Add some labels',
        autocompleter: { data: { ident: '', params: {} }, fetch_method: 'rest_autocomplete' },
        size: 7,
        id: 'test'
      }
    })

    const dropdown = screen.getByRole('combobox')
    await userEvent.click(dropdown)
    const input = screen.getByRole('textbox')
    await fireEvent.update(input, 'os')

    await waitFor(() => {
      expect(screen.getByRole('option', { name: 'OS Windows' })).toBeInTheDocument()
      expect(screen.getByRole('option', { name: 'OS Linux' })).toBeInTheDocument()
    })
  })

  test('on input should filter list', async () => {
    render(FormAutocompleter, {
      props: {
        placeholder: 'Add some labels',
        autocompleter: { data: { ident: '', params: {} }, fetch_method: 'rest_autocomplete' },
        size: 7,
        id: 'test'
      }
    })

    const dropdown = screen.getByRole('combobox')
    await userEvent.click(dropdown)
    const input = screen.getByRole('textbox')
    await fireEvent.update(input, 'os:w')

    await waitFor(() => {
      expect(screen.getByRole('option', { name: 'OS Windows' })).toBeInTheDocument()
      expect(screen.queryByRole('option', { name: 'OS Linux' })).not.toBeInTheDocument()
    })
  })

  test('on click on item from dropdown list should emit selected item', async () => {
    let selectedValue: string | null = ''
    render(FormAutocompleter, {
      props: {
        placeholder: 'Add some labels',
        autocompleter: { data: { ident: '', params: {} }, fetch_method: 'rest_autocomplete' },
        size: 7,
        id: 'test',
        'onUpdate:modelValue': (option: string | null) => {
          selectedValue = option
        }
      }
    })

    const dropdown = screen.getByRole('combobox')
    await userEvent.click(dropdown)
    const input = screen.getByRole('textbox')
    await fireEvent.update(input, 'os')

    await waitFor(() => {
      expect(screen.getByRole('option', { name: 'OS Windows' })).toBeInTheDocument()
    })
    await fireEvent.click(screen.getByRole('option', { name: 'OS Windows' }))

    expect(selectedValue).toBe('os:windows')
  })

  test('should emit selected item on pressing enter key on input after selecting item from dropdown list', async () => {
    let selectedValue: string | null = ''
    render(FormAutocompleter, {
      props: {
        placeholder: 'Add some labels',
        autocompleter: { data: { ident: '', params: {} }, fetch_method: 'rest_autocomplete' },
        size: 7,
        id: 'test',
        'onUpdate:modelValue': (option: string | null) => {
          selectedValue = option
        }
      }
    })

    const dropdown = screen.getByRole('combobox')

    // show suggestions of dropdown
    await userEvent.click(dropdown)

    // suggestions should show up
    await waitFor(() => {
      expect(screen.getByRole('option', { name: 'OS Windows' })).toBeInTheDocument()
      expect(screen.getByRole('option', { name: 'OS Linux' })).toBeInTheDocument()
    })

    await userEvent.type(screen.getByRole('textbox'), 'linux')

    // suggestions are filtered, so windows should go away
    await waitForElementToBeRemoved(() => screen.getByRole('option', { name: 'OS Windows' }))

    // lets choose the only element in the list
    await userEvent.keyboard('[ArrowDown][Enter]')

    await waitFor(() => {
      expect(selectedValue).toBe('os:linux')
    })
  })
})
