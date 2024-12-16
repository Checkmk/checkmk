/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import FormAutocompleter from '@/form/private/FormAutocompleter.vue'
import { ref, watch } from 'vue'
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'

vi.mock('@/form/components/utils/autocompleter', () => ({
  setupAutocompleter: vi.fn(() => {
    const input = ref('')
    const focus = ref(false)
    const output = ref()

    watch(input, async (newVal) => {
      if (newVal) {
        await new Promise((resolve) => setTimeout(resolve, 100))
        output.value = {
          choices: [
            ['os:windows', 'os:windows'],
            ['os:linux', 'os:linux']
          ].filter((item) => item[0]?.includes(newVal))
        }
      }
    })

    return { input, focus, output }
  })
}))

describe('FormAutocompleter', () => {
  test('should be rendered with placeholder', async () => {
    render(FormAutocompleter, {
      props: {
        placeholder: 'Search...',
        show: false,
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
    render(FormAutocompleter, {
      props: {
        placeholder: 'Search...',
        show: false,
        autocompleter: null,
        filterOn: [],
        resestInputOnAdd: false,
        size: 7,
        id: 'test'
      }
    }).emitted('select')

    const input = screen.getByPlaceholderText('Search...')
    await fireEvent.update(input, 'os:windows')
    await fireEvent.keyDown(input, { key: 'Enter' })
  })

  test('on input should open dropdown list with items', async () => {
    render(FormAutocompleter, {
      props: {
        placeholder: 'Add some labels',
        show: true,
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
      expect(screen.getByText('os:windows')).toBeInTheDocument()
      expect(screen.getByText('os:linux')).toBeInTheDocument()
    })

    const suggestions = screen.getAllByRole('listitem')
    expect(suggestions).toHaveLength(2)

    expect(suggestions[0]).toHaveTextContent('os:windows')
    expect(suggestions[1]).toHaveTextContent('os:linux')
  })

  test('on input should filter list', async () => {
    render(FormAutocompleter, {
      props: {
        placeholder: 'Add some labels',
        show: true,
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
      expect(screen.getByText('os:windows')).toBeInTheDocument()
      expect(screen.queryByText('os:linux')).not.toBeInTheDocument()
    })

    const suggestions = screen.getAllByRole('listitem')
    expect(suggestions).toHaveLength(1)

    expect(suggestions[0]).toHaveTextContent('os:windows')
  })

  test('on click on item from dropdown list should emit selected item', async () => {
    const component = render(FormAutocompleter, {
      props: {
        placeholder: 'Add some labels',
        show: true,
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
      expect(screen.getByText('os:windows')).toBeInTheDocument()
      expect(screen.getByText('os:linux')).toBeInTheDocument()
    })

    const suggestions = screen.getAllByRole('listitem')

    expect(suggestions).not.toHaveLength(0)
    if (suggestions[0]) {
      await fireEvent.click(suggestions[0])
    } else {
      throw new Error('No suggestions found')
    }

    expect(component.emitted('select')).toHaveLength(1)
  })

  test('should emit selected item on pressing enter key on input after selecting item from dropdown list', async () => {
    render(FormAutocompleter, {
      props: {
        placeholder: 'Add some labels',
        show: true,
        autocompleter: { data: { ident: '', params: {} }, fetch_method: 'ajax_vs_autocomplete' },
        filterOn: [],
        resestInputOnAdd: false,
        size: 7,
        id: 'test'
      }
    }).emitted('select')

    const input = screen.getByPlaceholderText('Add some labels')
    await fireEvent.update(input, 'os')

    await waitFor(() => {
      expect(screen.getByText('os:windows')).toBeInTheDocument()
      expect(screen.getByText('os:linux')).toBeInTheDocument()
    })
    const suggestions = screen.getAllByRole('listitem')
    expect(suggestions).not.toHaveLength(0)
    if (suggestions[0]) {
      await fireEvent.keyDown(input, { key: 'ArrowDown' })
      expect(suggestions[0].classList).toContain('selected')
      await fireEvent.keyDown(input, { key: 'Enter' })
    } else {
      throw new Error('No suggestions found')
    }

    await waitFor(() => {
      expect(screen.queryByText('os:windows')).not.toBeInTheDocument()
      expect(screen.queryByText('os:linux')).not.toBeInTheDocument()
    })
  })
})
