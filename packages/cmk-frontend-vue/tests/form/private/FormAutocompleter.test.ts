/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import FormAutocompleter from '@/form/private/FormAutocompleter.vue'
import { fireEvent, render, screen, waitFor, waitForElementToBeRemoved } from '@testing-library/vue'
import { Response } from '@/form/components/utils/autocompleter'
import userEvent from '@testing-library/user-event'

vi.mock(import('@/form/components/utils/autocompleter'), async (importOriginal) => {
  const mod = await importOriginal() // type is inferred
  return {
    ...mod,
    fetchSuggestions: vi.fn(async (_config: unknown, value: string) => {
      await new Promise((resolve) => setTimeout(resolve, 100))
      return new Response(
        [
          { name: 'os:windows', title: 'OS Windows' },
          { name: 'os:linux', title: 'OS Linux' }
        ].filter((item) => item.name.includes(value))
      )
    })
  }
})

describe('FormAutocompleter', () => {
  test('should be rendered with placeholder', async () => {
    render(FormAutocompleter, {
      props: {
        placeholder: 'Search...',
        filterOn: [],
        resetInputOnAdd: false,
        size: 7,
        id: 'test'
      }
    })
    expect(screen.getByPlaceholderText('Search...')).toBeInTheDocument()
  })

  test('shoud emit entered item on pressing enter key on input without selecting any item from dropdown list', async () => {
    let selectedValue: string | null = ''
    render(FormAutocompleter, {
      props: {
        placeholder: 'Search...',
        autocompleter: { data: { ident: '', params: {} }, fetch_method: 'ajax_vs_autocomplete' },
        filterOn: [],
        resetInputOnAdd: false,
        size: 7,
        id: 'test',
        'onUpdate:modelValue': (option: string | null) => {
          selectedValue = option
        }
      }
    })

    const input = screen.getByPlaceholderText('Search...')
    await fireEvent.update(input, 'os:windows')
    // TODO: we probably should switch to user-event, see
    // https://testing-library.com/docs/dom-testing-library/api-events/

    await waitFor(() => {
      expect(screen.getByText('OS Windows', { exact: false })).toBeInTheDocument()
    })

    await fireEvent.keyDown(input, { key: 'Enter' })

    expect(selectedValue).toBe('os:windows')
  })

  test('on focus should open dropdown list with items', async () => {
    render(FormAutocompleter, {
      props: {
        placeholder: 'Add some labels',
        autocompleter: { data: { ident: '', params: {} }, fetch_method: 'ajax_vs_autocomplete' },
        filterOn: [],
        resetInputOnAdd: false,
        size: 7,
        id: 'test'
      }
    })

    const input = screen.getByPlaceholderText('Add some labels')
    await fireEvent.focus(input)

    await waitFor(() => {
      expect(screen.getByText('OS Windows')).toBeInTheDocument()
      expect(screen.getByText('OS Linux')).toBeInTheDocument()
    })
  })

  test('on input should open dropdown list with items', async () => {
    render(FormAutocompleter, {
      props: {
        placeholder: 'Add some labels',
        autocompleter: { data: { ident: '', params: {} }, fetch_method: 'ajax_vs_autocomplete' },
        filterOn: [],
        resetInputOnAdd: false,
        size: 7,
        id: 'test'
      }
    })

    const input = screen.getByPlaceholderText('Add some labels')
    await fireEvent.update(input, 'os')

    await waitFor(() => {
      expect(screen.getByText('OS Windows')).toBeInTheDocument()
      expect(screen.getByText('OS Linux')).toBeInTheDocument()
    })
  })

  test('on input should filter list', async () => {
    render(FormAutocompleter, {
      props: {
        placeholder: 'Add some labels',
        autocompleter: { data: { ident: '', params: {} }, fetch_method: 'ajax_vs_autocomplete' },
        filterOn: [],
        resetInputOnAdd: false,
        size: 7,
        id: 'test'
      }
    })

    const input = screen.getByPlaceholderText('Add some labels')
    await fireEvent.update(input, 'os:w')

    await waitFor(() => {
      expect(screen.getByText('OS Windows')).toBeInTheDocument()
      expect(screen.queryByText('OS Linux')).not.toBeInTheDocument()
    })
  })

  test('on click on item from dropdown list should emit selected item', async () => {
    let selectedValue: string | null = ''
    render(FormAutocompleter, {
      props: {
        placeholder: 'Add some labels',
        autocompleter: { data: { ident: '', params: {} }, fetch_method: 'ajax_vs_autocomplete' },
        filterOn: [],
        resetInputOnAdd: false,
        size: 7,
        id: 'test',
        'onUpdate:modelValue': (option: string | null) => {
          selectedValue = option
        }
      }
    })

    const input = screen.getByPlaceholderText('Add some labels')
    await fireEvent.update(input, 'os')

    await waitFor(() => {
      expect(screen.getByText('OS Windows')).toBeInTheDocument()
    })
    await fireEvent.click(screen.getByText('OS Windows'))

    expect(selectedValue).toBe('os:windows')
  })

  test('should emit selected item on pressing enter key on input after selecting item from dropdown list', async () => {
    let selectedValue: string | null = ''
    render(FormAutocompleter, {
      props: {
        placeholder: 'Add some labels',
        autocompleter: { data: { ident: '', params: {} }, fetch_method: 'ajax_vs_autocomplete' },
        filterOn: [],
        resetInputOnAdd: false,
        size: 7,
        id: 'test',
        'onUpdate:modelValue': (option: string | null) => {
          selectedValue = option
        }
      }
    })

    const input = screen.getByPlaceholderText('Add some labels')

    // set cursor into text input field
    await userEvent.click(input)

    // suggestions should show up
    await waitFor(() => {
      expect(screen.getByText('OS Windows')).toBeInTheDocument()
      expect(screen.getByText('OS Linux')).toBeInTheDocument()
    })

    await userEvent.type(input, 'linux')

    // suggestions are filtered, so windows should go away
    await waitForElementToBeRemoved(() => screen.getByText('OS Windows'))

    // lets choose the only element in the list
    await userEvent.keyboard('[ArrowDown][Enter]')

    await waitFor(() => {
      expect(selectedValue).toBe('os:linux')
    })
  })
})
