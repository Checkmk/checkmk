/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, within } from '@testing-library/vue'
import FormLabel from '@/form/components/forms/FormLabels.vue'
import type * as FormSpec from '@/form/components/vue_formspec_components'
import { renderFormWithData } from '../cmk-form-helper'
import { ref, watch } from 'vue'

vitest.mock('@/form/components/utils/autocompleter', () => ({
  setupAutocompleter: () => [ref(''), ref({ choices: [['os:windows'], ['os:linux']] })]
}))

vitest.mock('@/form/components/utils/watch', () => ({
  immediateWatch: vitest.fn((source, callback) => {
    callback(source())
    return watch(source, callback, { immediate: true })
  })
}))

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
    add_some_labels: 'Add some labels',
    key_value_format_error:
      'Labels need to be in the format [KEY]:[VALUE]. For example os:windows.',
    max_labels_reached: 'You can only add up to 10 labels.',
    uniqueness_error: 'Labels need to be unique.'
  }
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

    const labelInput = await screen.findByPlaceholderText('Add some labels')
    expect(labelInput).toBeInTheDocument()
  })

  test('should add new label on pressing enter key after put a value in input', async () => {
    const { getCurrentData } = renderFormWithData({
      spec,
      data: { key1: 'value1', key2: 'value2' },
      backendValidation: []
    })

    const labelInput = await screen.findByPlaceholderText('Add some labels')
    await fireEvent.update(labelInput, 'key3:value3')
    await fireEvent.keyDown(labelInput, { key: 'Enter' })

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

  test('should not add label if it is already in the list and show a duplication error', async () => {
    const { getCurrentData } = renderFormWithData({
      spec,
      data: { key1: 'value1', key2: 'value2' },
      backendValidation: []
    })

    const labelInput = screen.getByPlaceholderText('Add some labels')

    await fireEvent.update(labelInput, 'key1:value1')
    await fireEvent.keyDown(labelInput, { key: 'Enter' })

    expect(getCurrentData()).toBe('{"key1":"value1","key2":"value2"}')

    screen.getByText('Labels need to be unique.')
  })

  test('should not add the label if the format is not like key:value and show a format error', async () => {
    const { getCurrentData } = renderFormWithData({
      spec,
      data: { key1: 'value1', key2: 'value2' },
      backendValidation: []
    })

    const labelInput = await screen.findByPlaceholderText('Add some labels')
    await fireEvent.update(labelInput, 'key1value1')
    await fireEvent.keyDown(labelInput, { key: 'Enter' })

    expect(getCurrentData()).toBe('{"key1":"value1","key2":"value2"}')

    screen.getByText('Labels need to be in the format [KEY]:[VALUE]. For example os:windows.')
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
})
