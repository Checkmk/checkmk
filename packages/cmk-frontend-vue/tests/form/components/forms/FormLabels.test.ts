/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { findByRole, fireEvent, render, screen, waitFor, within } from '@testing-library/vue'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'

import { Response } from '@/components/CmkSuggestions'

import FormLabel from '@/form/private/forms/FormLabels.vue'

import { renderForm } from '../cmk-form-helper'

const EXISTING_LABEL_KEY = 'existing_key'
const EXISTING_LABEL_VALUE = 'existing_value'
const EXISTING_LABEL_CONCAT = `${EXISTING_LABEL_KEY}:${EXISTING_LABEL_VALUE}`

vi.mock(import('@/form/private/FormAutocompleter/autocompleter'), async (importOriginal) => {
  const mod = await importOriginal() // type is inferred
  return {
    ...mod,
    fetchSuggestions: vi.fn(async (_config: unknown, value: string) => {
      let firstElement: Array<{ name: string; title: string }> = []
      if (value && /^.+:.+$/.test(value)) {
        firstElement = [{ name: value, title: value }]
      }
      await new Promise((resolve) => setTimeout(resolve, 100))
      return new Response([
        ...firstElement,
        ...[{ name: EXISTING_LABEL_CONCAT, title: EXISTING_LABEL_CONCAT }].filter((item) =>
          item.name.includes(value)
        )
      ])
    })
  }
})

const spec: FormSpec.Labels = {
  type: 'labels',
  title: 'Labels',
  help: 'Add some labels',
  validators: [],
  max_labels: 10,
  autocompleter: {
    fetch_method: 'ajax_vs_autocomplete',
    data: { ident: 'label', params: { world: 'config' } }
  },
  i18n: {
    remove_label: 'i18n remove_label',
    add_some_labels: 'Add some labels',
    key_value_format_error:
      'Labels need to be in the format [KEY]:[VALUE]. For example os:windows.',
    max_labels_reached: 'You can only add up to 10 labels.',
    uniqueness_error: 'Labels need to be unique.'
  },
  label_source: null
}

describe('FormLabels', () => {
  test('should be rendered with provided items and entry input', async () => {
    render(FormLabel, {
      props: {
        spec,
        data: { key1: 'value1', key2: 'value2' },
        backendValidation: []
      }
    })

    const labelList = await screen.findByRole('list')
    expect(labelList).toBeInTheDocument()
    const labelItems = await within(labelList).findAllByRole('listitem')
    expect(labelItems).toHaveLength(2)
    expect(labelList).toContainHTML('key1:value1')
    expect(labelList).toContainHTML('key2:value2')

    const dropdown = screen.getByRole('combobox')
    await userEvent.click(dropdown)
    const labelInput = screen.getByRole('textbox', { name: 'filter' })
    expect(labelInput).toBeInTheDocument()
  })

  test('should add new label on pressing enter key after put a value in input', async () => {
    const { getCurrentData } = await renderForm({
      spec,
      data: { key1: 'value1', key2: 'value2' },
      backendValidation: []
    })

    const dropdown = screen.getByRole('combobox')
    await userEvent.click(dropdown)
    const labelInput = screen.getByRole('textbox', { name: 'filter' })
    await userEvent.type(labelInput, 'key3:value3')

    await screen.findByText('key3:value3')

    await userEvent.keyboard('[Enter]')

    expect(getCurrentData()).toBe('{"key1":"value1","key2":"value2","key3":"value3"}')
  })

  test('should remove label on clicking on remove button', async () => {
    const { getCurrentData } = await renderForm({
      spec,
      data: { key1: 'value1', key2: 'value2' },
      backendValidation: []
    })

    const ulElement = await screen.findByRole('list')
    const labelList = await within(ulElement).findAllByRole('listitem')
    const removeButtons = labelList.map((labelItem) => within(labelItem).getByRole('button'))

    expect(removeButtons).toHaveLength(2)

    const removeButton = removeButtons[0]
    if (removeButton) {
      await fireEvent.click(removeButton)
    }
    expect(getCurrentData()).toBe('{"key2":"value2"}')
  })

  test('should suggest existing labels', async () => {
    await renderForm({
      spec,
      data: {},
      backendValidation: []
    })

    const dropdown = screen.getByRole('combobox')
    await userEvent.click(dropdown)
    const labelInput = screen.getByRole('textbox', { name: 'filter' })

    await fireEvent.update(labelInput, `${EXISTING_LABEL_KEY}:`)
    await screen.findByText(EXISTING_LABEL_CONCAT)
  })

  test.for([
    ['missing value', `asd:`],
    ['already chosen label', EXISTING_LABEL_CONCAT],
    ['same key prefix', `${EXISTING_LABEL_KEY}:something`]
  ] as Array<[string, string]>)('should suggest nothing for %s', async ([_name, label]) => {
    await renderForm({
      spec,
      data: { [EXISTING_LABEL_KEY]: EXISTING_LABEL_VALUE },
      backendValidation: []
    })

    async function assertNumberOfOptions(number: number) {
      await waitFor(async () => expect(screen.queryAllByRole('option')).toHaveLength(number))
    }

    const dropdown = screen.getByRole('combobox')
    await userEvent.click(dropdown)
    const labelInput = screen.getByRole('textbox', { name: 'filter' })

    // we want to assert that the list is empty, so we have to make sure there is something before
    await fireEvent.update(labelInput, 'something:anything')
    await assertNumberOfOptions(1)

    await fireEvent.update(labelInput, label)
    await assertNumberOfOptions(0)
  })

  test('should allow remove label', async () => {
    const { getCurrentData } = await renderForm({
      spec,
      data: { key1: 'value1', key2: 'value2' },
      backendValidation: []
    })

    const ulElement = await screen.findByRole('list')
    const labelList = await within(ulElement).findAllByRole('listitem')
    expect(labelList).toHaveLength(2)

    await userEvent.click(await findByRole(labelList[1]!, 'button', { name: 'Remove element' }))

    await waitFor(() => expect(getCurrentData()).toBe('{"key1":"value1"}'))
  })

  test('should reset selection input element on add item', async () => {
    const { getCurrentData } = await renderForm({
      spec,
      data: {},
      backendValidation: []
    })

    const dropdown = screen.getByRole('combobox')
    await userEvent.click(dropdown)
    const labelInput = screen.getByRole('textbox', { name: 'filter' })
    await userEvent.type(labelInput, 'key3:value3')
    await screen.findByText('key3:value3')
    await userEvent.keyboard('[Enter]')
    expect(getCurrentData()).toBe('{"key3":"value3"}')

    await screen.findByText('Add some labels')
  })
})
