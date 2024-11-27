/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { FormSpec, Dictionary } from '@/form/components/vue_formspec_components'
import FormSingleChoiceEditableEditAsync from '@/form/components/forms/FormSingleChoiceEditableEditAsync.vue'
import type { SetDataResult } from '@/form/components/forms/FormSingleChoiceEditableEditAsync.vue'
import FormEditDispatcher from '@/form/components/FormEditDispatcher.vue'
import { dispatcherKey } from '@/form/private'
import { screen, render } from '@testing-library/vue'

test('FormSingleChoiceEditableEditAsync renders form', async () => {
  type Data = Record<string, unknown>

  render(FormSingleChoiceEditableEditAsync<string, Data>, {
    global: {
      provide: {
        [dispatcherKey]: FormEditDispatcher
      }
    },
    props: {
      objectId: null,
      api: {
        getSchema: async function (): Promise<FormSpec> {
          const dict: Dictionary = {
            type: 'dictionary',
            no_elements_text: 'no elements text',
            additional_static_elements: [],
            title: 'dict title',
            validators: [],
            help: 'dict help',
            elements: [
              {
                name: 'element_ident',
                group: null,
                required: false,
                default_value: '',
                parameter_form: {
                  type: 'string',
                  title: 'string title',
                  help: 'some string help',
                  validators: []
                }
              }
            ],
            layout: 'one_column',
            groups: []
          }
          return dict
        },
        getData: async function (objectId: string | null): Promise<Data> {
          return { element_ident: `some_data ${objectId}` }
        },
        setData: async function (
          _objectId: string | null,
          _data: Data
        ): Promise<SetDataResult<Data>> {
          return { type: 'success', entity: { id: 'some_object_id' } }
        }
      },
      i18n: {
        save_button: 'save_button_i18n',
        cancel_button: 'cancel_button_i18n',
        create_button: 'create_button_i18n',
        validation_error: 'validation_button_i18n',
        loading: 'loading_i18n',
        fatal_error: 'fatal_error_i18n'
      }
    }
  })

  // form is rendered correctly
  const stringInput = await screen.findByRole<HTMLInputElement>('textbox', { name: 'string title' })

  // data of form is visible in form
  expect(stringInput.value).toBe('some_data null')
})
