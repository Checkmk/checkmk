/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import FormCatalog from '@/form/components/forms/form_catalog/FormCatalog.vue'
import type {
  String as StringSpec,
  Dictionary as DictionarySpec,
  DictionaryElement,
  Catalog
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import { renderFormWithData } from '../cmk-form-helper'

type PartialExcept<T, K extends keyof T> = Pick<T, K> & Partial<Omit<T, K>>

function getStringFormspec(
  title: string,
  options?: Partial<Omit<DictionarySpec, 'type'>>
): StringSpec {
  return {
    type: 'string',
    title: title,
    label: null,
    help: `ut help ${title}`,
    i18n_base: { required: 'required' },
    validators: [],
    input_hint: `ut input hint ${title}`,
    field_size: 'SMALL',
    autocompleter: null,
    ...options
  }
}

function getDictionaryFormspec(
  dictionaryOptions: Partial<DictionarySpec>,
  elements: Array<PartialExcept<DictionaryElement, 'name' | 'parameter_form'>>
): DictionarySpec {
  return {
    type: 'dictionary',
    title: 'dictionary title',
    help: 'dictionary help',
    i18n_base: { required: 'required' },
    groups: [],
    validators: [],
    no_elements_text: 'ut no elements text',
    additional_static_elements: null,
    elements: elements.map((element) => {
      return {
        required: false,
        render_only: false,
        default_value: '',
        group: null,
        ...element
      }
    }),
    ...dictionaryOptions
  }
}

function renderSimpleCatalog() {
  return render(FormCatalog, {
    props: {
      spec: {
        type: 'catalog',
        title: 'catalog title',
        help: 'catalog help',
        validators: [],
        i18n_base: { required: 'required' },
        elements: [
          {
            name: 'main_topic',
            title: 'topic_title',
            elements: [
              {
                type: 'topic_element',
                name: 'dict_key',
                required: true,
                default_value: {},
                parameter_form: getDictionaryFormspec(
                  {
                    title: 'dict_title'
                    // this title will be moved into the catalog and displayed there a stitle
                  },
                  [
                    {
                      name: 'ut_string_1',
                      parameter_form: getStringFormspec('title of string input'),
                      group: null
                    }
                  ]
                )
              }
            ]
          }
        ]
      },
      data: { main_topic: { dict_key: { some_ut_key: {} } } }, // TODO: some_ut_key is required. should it be?
      backendValidation: []
    }
  })
}

test('FormCatalog open/close topic', async () => {
  renderSimpleCatalog()

  const headline = await screen.findByText('topic_title')
  const img = headline.querySelector('img')
  // the visibility of elements is changed via classes and css, but the css is not
  // available in the tests, so we have to manually check if the classes are added.
  // TODO: we should really change our code to make the following possible:
  // it should be quite easy to use v-show for that...
  // expect(title).not.toBeVisible()
  expect(img).toHaveClass('open')
  expect(img).not.toHaveClass('closed')

  await fireEvent.click(headline)
  expect(img).not.toHaveClass('open')
  expect(img).toHaveClass('closed')

  await fireEvent.click(headline)
  expect(img).toHaveClass('open')
  expect(img).not.toHaveClass('closed')
})

test.skip('FormCatalog collapse/open all - skipped until the toggle gets a better implementation', async () => {
  renderSimpleCatalog()
  await screen.findByText('title of string input')

  const headline = await screen.findByText('ut embedded dictionary title')
  const parent = headline.parentElement!.parentElement!.parentElement!
  expect(parent).toHaveClass('open')
  expect(parent).not.toHaveClass('closed')

  await fireEvent.click(screen.getByText('Collapse all'))
  expect(parent).toHaveClass('closed')
  expect(parent).not.toHaveClass('open')

  await fireEvent.click(screen.getByText('Open all'))
  expect(parent).toHaveClass('open')
  expect(parent).not.toHaveClass('closed')
})

test('FormCatalog default value', async () => {
  function getDefinition(stringIdent: string) {
    return {
      spec: {
        type: 'catalog',
        title: 'catalog title',
        help: 'catalog help',
        i18n_base: { required: 'required' },
        validators: [],
        elements: [
          {
            name: 'topic_name',
            title: 'topic_title',
            elements: [
              {
                name: 'some_ut_key',
                type: 'topic_element',
                required: true,
                default_value: {},
                parameter_form: getDictionaryFormspec(
                  {
                    title: 'ut embedded dictionary title'
                    // this title will be moved into the catalog and displayed there a title
                  },
                  [
                    {
                      name: stringIdent,
                      required: true,
                      parameter_form: getStringFormspec('title of string input'),
                      default_value: 'ut_string_1 default value'
                    }
                  ]
                )
              }
            ]
          }
        ]
      } as Catalog,
      data: { topic_name: { some_ut_key: {} } },
      backendValidation: []
    }
  }
  const { getCurrentData, rerender } = renderFormWithData(getDefinition('ut_string_1_name_default'))

  // wait until everything is rendered:
  await screen.findByText('title of string input')

  expect(getCurrentData()).toBe(
    '{"topic_name":{"some_ut_key":{"ut_string_1_name_default":"ut_string_1 default value"}}}'
  )

  await rerender(getDefinition('some_other_string_indent'))

  expect(getCurrentData()).toBe(
    '{"topic_name":{"some_ut_key":{"some_other_string_indent":"ut_string_1 default value"}}}'
  )
})

test('FormCatalog backend validation', async () => {
  const spec = {
    spec: {
      type: 'catalog',
      title: 'catalog title',
      help: 'catalog help',
      i18n_base: { required: 'required' },
      validators: [],
      elements: [
        {
          name: 'topic_name',
          title: 'topic_title',
          elements: [
            {
              name: 'ut_topic_element_1',
              type: 'topic_element',
              default_value: {},
              required: true,
              parameter_form: getDictionaryFormspec({}, [
                {
                  name: 'ut_topic_1_dict_1',
                  parameter_form: getStringFormspec('ut_topic_1_dict_1_key_1')
                }
              ])
            },
            {
              name: 'ut_topic_element_2',
              type: 'topic_element',
              default_value: {},
              required: true,
              parameter_form: getDictionaryFormspec({}, [
                {
                  name: 'ut_topic_2_dict_1',
                  parameter_form: getStringFormspec('ut_topic_2_dict_1_key_1')
                }
              ])
            }
          ]
        }
      ]
    } as Catalog,
    data: {
      topic_name: {
        ut_topic_element_1: { ut_topic_1_dict_1: '' },
        ut_topic_element_2: { ut_topic_2_dict_1: '' }
      }
    },
    backendValidation: [
      {
        location: ['topic_name', 'ut_topic_element_1', 'ut_topic_1_dict_1'],
        message: 'ut_error_1',
        replacement_value: ''
      },
      {
        location: ['topic_name', 'ut_topic_element_2', 'ut_topic_2_dict_1'],
        message: 'ut_error_2',
        replacement_value: ''
      }
    ]
  }
  renderFormWithData(spec)
  expect(await screen.findAllByText('ut_error_1')).toHaveLength(1)
  expect(await screen.findAllByText('ut_error_2')).toHaveLength(1)
})
