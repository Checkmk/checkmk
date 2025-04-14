/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, within } from '@testing-library/vue'
import FormLabel from '@/form/components/forms/FormLabels.vue'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import { renderFormWithData } from '../cmk-form-helper'
import userEvent from '@testing-library/user-event'
import { Response } from '@/components/suggestions'

const EXISTING_LABEL_KEY = 'existing_key'
const EXISTING_LABEL_VALUE = 'existing_value'
const EXISTING_LABEL_CONCAT = `${EXISTING_LABEL_KEY}:${EXISTING_LABEL_VALUE}`

vi.mock(import('@/form/components/utils/autocompleter'), async (importOriginal) => {
  const mod = await importOriginal() // type is inferred
  return {
    ...mod,
    fetchSuggestions: vi.fn(async (_config: unknown, value: string) => {
      let firstElement: Array<{ name: string; title: string }> = []
      if (value) {
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
    const { getCurrentData } = renderFormWithData({
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
    const { getCurrentData } = renderFormWithData({
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
    renderFormWithData({
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

  test('should not suggest used existing labels', async () => {
    renderFormWithData({
      spec,
      data: { [EXISTING_LABEL_KEY]: EXISTING_LABEL_VALUE },
      backendValidation: []
    })

    const dropdown = screen.getByRole('combobox')
    await userEvent.click(dropdown)
    const labelInput = screen.getByRole('textbox', { name: 'filter' })

    await fireEvent.update(labelInput, `${EXISTING_LABEL_KEY}:`)
    await screen.findByText(`${EXISTING_LABEL_KEY}:`)

    expect(screen.queryByText(EXISTING_LABEL_CONCAT)).toBeNull()
    // not sure if this test is meaninfull, as everything takes some time to update?!
  })

  test('should warn about duplicates', async () => {
    renderFormWithData({
      spec,
      data: { some: 'thing' },
      backendValidation: []
    })

    // make sure that we see the label, if our current value is something different
    let dropdown = screen.getByRole('combobox')
    await userEvent.click(dropdown)
    await screen.findByRole('option')
    await screen.findByText(EXISTING_LABEL_CONCAT)

    // but we should not see a suggestion if the data and the only existing
    // label is the same
    document.body.innerHTML = '' // TODO: CHECK IF NECESSARY!
    renderFormWithData({
      spec,
      data: { [EXISTING_LABEL_KEY]: EXISTING_LABEL_VALUE },
      backendValidation: []
    })

    dropdown = screen.getByRole('combobox')
    await userEvent.click(dropdown)
    // TODO: this is completly useless
    // if you copy the next line after the first click(dropdown), the test will
    // also pass! i fear we have to remove this test?!
    expect(screen.queryByRole('option')).toBeNull()
    expect(screen.queryByText(EXISTING_LABEL_CONCAT)).toBeNull()
    // also: this is (now) a duplicate of the previous test?!
  })

  test('should allow edit label', async () => {
    const { getCurrentData } = renderFormWithData({
      spec,
      data: { key1: 'value1', key2: 'value2' },
      backendValidation: []
    })

    const ulElement = await screen.findByRole('list')
    const labelList = await within(ulElement).findAllByRole('listitem')
    expect(labelList).toHaveLength(2)

    const label = labelList[0] ? await within(labelList[0]).findByRole('textbox') : null
    if (!label) {
      throw new Error('Label not found')
    }

    const inputElement = label as HTMLInputElement

    await fireEvent.click(inputElement)
    await fireEvent.update(inputElement, 'key1:value1_edited')

    expect(inputElement.value).toBe('key1:value1_edited')
    await fireEvent.keyDown(inputElement, { key: 'Enter' })

    expect(getCurrentData()).toBe('{"key1":"value1_edited","key2":"value2"}')
  })

  test('should reset selection label', async () => {
    const { getCurrentData } = renderFormWithData({
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

    expect(dropdown.textContent).toBe('key3:value3') // FIX ME: should be empty!
  })
})
