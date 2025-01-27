/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import FormAutocompleter from '@/form/private/FormAutocompleter.vue'
import { ref, watch } from 'vue'
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'

vi.mock('@/form/components/utils/autocompleter', () => ({
  setupAutocompleter: vi.fn(() => {
    const input = ref('')
    const output = ref()

    watch(input, async (newVal) => {
      if (newVal) {
        await new Promise((resolve) => setTimeout(resolve, 100))
        output.value = {
          choices: [
            ['os:windows', 'OS Windows'],
            ['os:linux', 'OS Linux']
          ].filter((item) => item[0]?.includes(newVal))
        }
      }
    })

    return { input, output }
  })
}))

describe('FormAutocompleter', () => {
  test('should be rendered with placeholder', async () => {
    render(FormAutocompleter, {
      props: {
        placeholder: 'Search...',
        autocompleter: null,
        filterOn: [],
        resestInputOnAdd: false,
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
        autocompleter: null,
        filterOn: [],
        resestInputOnAdd: false,
        size: 7,
        id: 'test',
        'onUpdate:modelValue': (option: string | null) => {
          selectedValue = option
        }
      }
    })

    const input = screen.getByPlaceholderText('Search...')
    await fireEvent.update(input, 'os:windows')

    await waitFor(() => {
      expect(screen.getByText('OS Windows', { exact: false })).toBeInTheDocument()
    })

    await fireEvent.keyDown(input, { key: 'Enter' })

    expect(selectedValue).toBe('os:windows')
  })

  test('on input should open dropdown list with items', async () => {
    render(FormAutocompleter, {
      props: {
        placeholder: 'Add some labels',
        autocompleter: { data: { ident: '', params: {} }, fetch_method: 'ajax_vs_autocomplete' },
        filterOn: [],
        resestInputOnAdd: false,
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
        resestInputOnAdd: false,
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
        resestInputOnAdd: false,
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
        resestInputOnAdd: false,
        size: 7,
        id: 'test',
        'onUpdate:modelValue': (option: string | null) => {
          selectedValue = option
        }
      }
    })

    const input = screen.getByPlaceholderText('Add some labels')
    await userEvent.type(input, 'os')

    await waitFor(() => {
      expect(screen.getByText('OS Windows')).toBeInTheDocument()
      expect(screen.getByText('OS Linux')).toBeInTheDocument()
    })

    await userEvent.keyboard('[ArrowDown][Enter]')

    expect(selectedValue).toBe('os:linux')
  })
})
