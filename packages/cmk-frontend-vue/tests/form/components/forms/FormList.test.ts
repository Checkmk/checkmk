/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import { mount } from '@vue/test-utils'
import FormList from '@/form/components/forms/FormList.vue'
import FormEdit from '@/form/components/FormEdit.vue'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import { renderFormWithData } from '../cmk-form-helper'
import FormDataVisualizer from '../FormDataVisualizer.vue'

const stringValidators: FormSpec.Validator[] = [
  {
    type: 'length_in_range',
    min_value: 1,
    max_value: 20,
    error_message: 'String length must be between 1 and 20'
  }
]

const stringFormSpec: FormSpec.String = {
  type: 'string',
  title: 'barTitle',
  help: 'barHelp',
  label: null,
  i18n_base: { required: 'required' },
  validators: stringValidators,
  input_hint: '',
  autocompleter: null,
  field_size: 'SMALL'
}

const dictElementGroupFormSpec: FormSpec.DictionaryGroup = {
  key: 'titlehelp',
  title: 'title',
  help: 'help',
  layout: 'horizontal'
}

const spec: FormSpec.List = {
  type: 'list',
  title: 'fooTitle',
  help: 'fooHelp',
  validators: [],
  element_template: stringFormSpec,
  element_default_value: '',
  editable_order: true,
  add_element_label: 'Add element',
  remove_element_label: 'Remove element',
  no_element_label: 'No element'
}

test.skip('List elements are draggable', async () => {
  // This test is skipped because the drag and drop functionality is not working
  // in the test environment. There would be a way to test the implementation
  // details but since the browser behavior is so far removed from just reacting
  // to events, we do not gain anything from it besides a lot of complexity.
  const wrapper = mount(FormDataVisualizer, {
    props: {
      spec,
      data: ['first_value', 'second_value'],
      backendValidation: []
    }
  })

  const draggables = wrapper.findAll('[aria-label="Drag to reorder"]')
  await draggables[0]!.trigger('dragstart')
  await draggables[0]!.trigger('drag', { clientX: 0, clientY: 50 })
  await draggables[0]!.trigger('dragend')

  wrapper.vm.$nextTick(() => {
    expect(wrapper.find('[data-testid="test-data"]').text()).toBe('["second_value","first_value"]')
  })
})

test('FormList renders backend validation messages', async () => {
  render(FormList, {
    props: {
      spec,
      data: [],
      backendValidation: [{ location: [], message: 'Backend error message', replacement_value: '' }]
    }
  })

  screen.getByText('Backend error message')
})

test.skip('FormList updated backend child validation shows validation error', async () => {
  const { rerender } = render(FormList, {
    props: {
      spec,
      data: ['some value'],
      backendValidation: []
    }
  })

  expect(screen.queryByText('Backend error message')).toBeNull()

  await rerender({
    spec,
    data: ['some value'],
    backendValidation: [
      { location: ['0'], message: 'Backend error message', replacement_value: 'other value' }
    ]
  })

  screen.getByText('Backend error message')
  const textbox = screen.getByRole<HTMLInputElement>('textbox')
  expect(textbox.value).toBe('other value')
})

test('FormList local child validation overwrites backend validation', async () => {
  render(FormEdit, {
    props: {
      spec,
      data: ['some value'],
      backendValidation: [
        { location: ['0'], message: 'Backend error message', replacement_value: 'other value' }
      ]
    }
  })

  const textbox = await screen.findByRole<HTMLInputElement>('textbox')
  await fireEvent.update(textbox, '')

  screen.getByText('String length must be between 1 and 20')
  expect(screen.queryByText('Backend error message')).toBeNull()
})

test('FormList shows frontend validation on existing element', async () => {
  render(FormEdit, {
    props: {
      spec,
      data: ['some_value'],
      backendValidation: []
    }
  })

  const textbox = await screen.findByRole<HTMLInputElement>('textbox')
  await fireEvent.update(textbox, '')

  screen.getByText('String length must be between 1 and 20')
})

const dictSpec: FormSpec.Dictionary = {
  type: 'dictionary',
  title: 'dictTitle',
  help: 'fooHelp',
  i18n_base: { required: 'required' },
  validators: [],
  groups: [],
  no_elements_text: 'no_text',
  additional_static_elements: null,
  elements: [
    {
      name: 'bar',
      render_only: false,
      required: true,
      default_value: 'baz',
      parameter_form: stringFormSpec,
      group: dictElementGroupFormSpec
    }
  ]
}

const listSpec: FormSpec.List = {
  type: 'list',
  title: 'fooTitle',
  help: 'fooHelp',
  validators: [],
  element_template: dictSpec,
  element_default_value: {},
  editable_order: false,
  add_element_label: 'Add element',
  remove_element_label: 'Remove element',
  no_element_label: 'No element'
}

test('FormList adds two new elements and enters data', async () => {
  const { getCurrentData } = renderFormWithData({
    spec: listSpec,
    data: [],
    backendValidation: []
  })

  const addElementButton = await screen.getByText('Add element')
  await fireEvent.click(addElementButton)
  await fireEvent.click(addElementButton)

  const element = await screen.getAllByRole('textbox')
  await fireEvent.update(element[0]!, '1234')
  expect(getCurrentData()).toMatch('[{"bar":"1234"},{"bar":"baz"}]')
})
