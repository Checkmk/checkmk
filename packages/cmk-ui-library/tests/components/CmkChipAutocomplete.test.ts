/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import CmkChipAutocomplete from 'cmk-ui-library/components/CmkChipAutocomplete.vue'
import { ref } from 'vue'

const VALUES = ['cmk/os_family:linux', 'cmk/os_family:windows', 'criticality:prod']

function mountChips(
  options: { selected?: string[]; maxSelected?: number; suggestWhenEmpty?: boolean } = {}
) {
  const selected = ref<string[]>(options.selected ?? [])
  const suggest = vi.fn((query: string) =>
    Promise.resolve(VALUES.filter((value) => value.includes(query)))
  )
  const result = render(CmkChipAutocomplete, {
    props: {
      suggest,
      modelValue: selected.value,
      'onUpdate:modelValue': (value: string[]) => {
        selected.value = value
      },
      ...(options.maxSelected === undefined ? {} : { maxSelected: options.maxSelected }),
      ...(options.suggestWhenEmpty === undefined
        ? {}
        : { suggestWhenEmpty: options.suggestWhenEmpty })
    }
  })
  return { ...result, selected, suggest }
}

test('asks for nothing before anything is typed', () => {
  const { suggest } = mountChips()

  expect(suggest).not.toHaveBeenCalled()
  expect(screen.queryByRole('button')).not.toBeInTheDocument()
})

test('seeds the list on focus when asked to', async () => {
  mountChips({ suggestWhenEmpty: true })

  await userEvent.click(screen.getByRole('textbox'))

  await waitFor(() => {
    expect(screen.getByRole('button', { name: 'criticality:prod' })).toBeInTheDocument()
  })
})

test('suggests what the typed text matches', async () => {
  mountChips()

  await userEvent.type(screen.getByRole('textbox'), 'os_family')

  await waitFor(() => {
    expect(screen.getByRole('button', { name: 'cmk/os_family:linux' })).toBeInTheDocument()
  })
  expect(screen.queryByRole('button', { name: 'criticality:prod' })).not.toBeInTheDocument()
})

test('turns a picked suggestion into a chip and clears the input', async () => {
  const { rerender, selected } = mountChips()

  await userEvent.type(screen.getByRole('textbox'), 'linux')
  await waitFor(() => screen.getByRole('button', { name: 'cmk/os_family:linux' }))
  await userEvent.click(screen.getByRole('button', { name: 'cmk/os_family:linux' }))

  expect(selected.value).toEqual(['cmk/os_family:linux'])
  await rerender({ modelValue: selected.value })
  expect(screen.getByRole('textbox')).toHaveValue('')
  expect(screen.getByRole('button', { name: 'Remove cmk/os_family:linux' })).toBeInTheDocument()
})

test('moves focus into the suggestions with the arrow keys', async () => {
  mountChips()

  await userEvent.type(screen.getByRole('textbox'), 'os_family')
  await waitFor(() => screen.getByRole('button', { name: 'cmk/os_family:linux' }))
  await userEvent.keyboard('{ArrowDown}')

  expect(screen.getByRole('button', { name: 'cmk/os_family:linux' })).toHaveFocus()

  await userEvent.keyboard('{ArrowDown}')
  expect(screen.getByRole('button', { name: 'cmk/os_family:windows' })).toHaveFocus()

  await userEvent.keyboard('{ArrowUp}')
  expect(screen.getByRole('button', { name: 'cmk/os_family:linux' })).toHaveFocus()
})

test('selects the focused suggestion with the keyboard', async () => {
  const { selected } = mountChips()

  await userEvent.type(screen.getByRole('textbox'), 'linux')
  await waitFor(() => screen.getByRole('button', { name: 'cmk/os_family:linux' }))
  await userEvent.keyboard('{ArrowDown}{Enter}')

  expect(selected.value).toEqual(['cmk/os_family:linux'])
})

test('drops the chip added last on backspace in an empty input', async () => {
  const { selected } = mountChips({ selected: ['criticality:prod', 'cmk/site:heute'] })

  await userEvent.click(screen.getByRole('textbox'))
  await userEvent.keyboard('{Backspace}')

  expect(selected.value).toEqual(['criticality:prod'])
})

test('drops a chip through its remove button', async () => {
  const { selected } = mountChips({ selected: ['criticality:prod'] })

  await userEvent.click(screen.getByRole('button', { name: 'Remove criticality:prod' }))

  expect(selected.value).toEqual([])
})

test('never suggests what is already selected', async () => {
  mountChips({ selected: ['cmk/os_family:linux'] })

  await userEvent.type(screen.getByRole('textbox'), 'os_family')

  await waitFor(() => {
    expect(screen.getByRole('button', { name: 'cmk/os_family:windows' })).toBeInTheDocument()
  })
  expect(screen.queryByRole('button', { name: 'cmk/os_family:linux' })).not.toBeInTheDocument()
})

test('says so when nothing matches', async () => {
  mountChips()

  await userEvent.type(screen.getByRole('textbox'), 'nothing-matches-this')

  await waitFor(() => {
    expect(screen.getByText('No matching values')).toBeInTheDocument()
  })
})

test('refuses further picks once maxSelected is reached', async () => {
  const { selected } = mountChips({ selected: ['criticality:prod'], maxSelected: 1 })

  await userEvent.type(screen.getByRole('textbox'), 'os_family')

  await waitFor(() => {
    expect(screen.getByRole('button', { name: 'cmk/os_family:linux' })).toBeDisabled()
  })
  await userEvent.click(screen.getByRole('button', { name: 'cmk/os_family:linux' }))
  expect(selected.value).toEqual(['criticality:prod'])
})

test('keeps only the newest response when an earlier one resolves late', async () => {
  const selected = ref<string[]>([])
  const resolvers: Array<(values: string[]) => void> = []
  render(CmkChipAutocomplete, {
    props: {
      suggest: (_query: string) =>
        new Promise<string[]>((resolve) => {
          resolvers.push(resolve)
        }),
      modelValue: selected.value,
      'onUpdate:modelValue': (value: string[]) => {
        selected.value = value
      }
    }
  })

  await userEvent.type(screen.getByRole('textbox'), 'a')
  await waitFor(() => expect(resolvers).toHaveLength(1))
  await userEvent.type(screen.getByRole('textbox'), 'b')
  await waitFor(() => expect(resolvers).toHaveLength(2))

  resolvers[1]!(['newest'])
  resolvers[0]!(['stale'])

  await waitFor(() => {
    expect(screen.getByRole('button', { name: 'newest' })).toBeInTheDocument()
  })
  expect(screen.queryByRole('button', { name: 'stale' })).not.toBeInTheDocument()
})

const PAIRS = ['cmk/os_family:linux', 'cmk/os_family:windows', 'criticality:prod']

function mountKeyValue(options: { wildcardOption?: boolean } = {}) {
  const selected = ref<string[]>([])
  const suggest = (query: string) =>
    Promise.resolve(PAIRS.filter((pair) => pair.includes(query.trim().toLowerCase())))
  const result = render(CmkChipAutocomplete, {
    props: {
      suggest,
      keyValue: true,
      modelValue: selected.value,
      'onUpdate:modelValue': (value: string[]) => {
        selected.value = value
      },
      ...(options.wildcardOption === undefined ? {} : { wildcardOption: options.wildcardOption })
    }
  })
  return { ...result, selected }
}

test('picking a bare key continues the query instead of committing a chip', async () => {
  const { selected } = mountKeyValue()

  await userEvent.type(screen.getByRole('textbox'), 'os_family')
  await waitFor(() => screen.getByRole('button', { name: 'cmk/os_family' }))
  await userEvent.click(screen.getByRole('button', { name: 'cmk/os_family' }))

  expect(selected.value).toEqual([])
  expect(screen.getByRole('textbox')).toHaveValue('cmk/os_family:')
})

test('picking the value of a key commits the pair', async () => {
  const { selected } = mountKeyValue()

  await userEvent.type(screen.getByRole('textbox'), 'os_family')
  await waitFor(() => screen.getByRole('button', { name: 'cmk/os_family' }))
  await userEvent.click(screen.getByRole('button', { name: 'cmk/os_family' }))

  await waitFor(() => screen.getByRole('button', { name: 'cmk/os_family:linux' }))
  await userEvent.click(screen.getByRole('button', { name: 'cmk/os_family:linux' }))

  expect(selected.value).toEqual(['cmk/os_family:linux'])
  expect(screen.getByRole('textbox')).toHaveValue('')
})

test('commits a pair straight away when the suggestion already carries a value', async () => {
  const { selected } = mountKeyValue()

  await userEvent.type(screen.getByRole('textbox'), 'criticality:')
  await waitFor(() => screen.getByRole('button', { name: 'criticality:prod' }))
  await userEvent.click(screen.getByRole('button', { name: 'criticality:prod' }))

  expect(selected.value).toEqual(['criticality:prod'])
})

test('offers the keys of what came back in their own right', async () => {
  mountKeyValue()

  await userEvent.type(screen.getByRole('textbox'), 'os_family')

  await waitFor(() => {
    expect(screen.getByRole('button', { name: 'cmk/os_family' })).toBeInTheDocument()
  })
  expect(screen.getByRole('button', { name: 'cmk/os_family:linux' })).toBeInTheDocument()
})

test('offers no wildcard entry unless asked for one', async () => {
  mountKeyValue()

  await userEvent.type(screen.getByRole('textbox'), 'os_family')

  await waitFor(() => screen.getByRole('button', { name: 'cmk/os_family' }))
  expect(screen.queryByRole('button', { name: 'os_family*' })).not.toBeInTheDocument()
})

test('lists the wildcard entry first and commits it as typed', async () => {
  const { selected } = mountKeyValue({ wildcardOption: true })

  await userEvent.type(screen.getByRole('textbox'), 'os_family')
  await waitFor(() => screen.getByRole('button', { name: 'os_family*' }))

  const listed = screen.getAllByRole('button').map((button) => button.textContent?.trim())
  expect(listed[0]).toBe('os_family*')

  await userEvent.click(screen.getByRole('button', { name: 'os_family*' }))
  expect(selected.value).toEqual(['os_family*'])
})
