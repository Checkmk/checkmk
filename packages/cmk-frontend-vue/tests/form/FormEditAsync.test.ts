/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import { flushPromises } from '@vue/test-utils'
import type {
  Dictionary,
  FormSpec,
  String
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import { vi } from 'vitest'

import FormSingleChoiceEditableEditAsync from '@/form/FormEditAsync.vue'
import type { SetDataResult } from '@/form/FormEditAsync.vue'
import FormEditDispatcher from '@/form/private/FormEditDispatcher/FormEditDispatcher.vue'
import { dispatcherKey } from '@/form/private/FormEditDispatcher/useFormEditDispatcher'

const defaultI18n = {
  save_button: 'save_button_i18n',
  cancel_button: 'cancel_button_i18n',
  create_button: 'create_button_i18n',
  validation_error: 'validation_button_i18n',
  loading: 'loading_i18n',
  fatal_error: 'fatal_error_i18n',
  permanent_choice_warning: 'permanent_choice_warning_i18n',
  permanent_choice_warning_dismissal: 'permanent_choice_warning_dismissal_i18n'
}

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
                render_only: false,
                group: null,
                required: false,
                default_value: '',
                parameter_form: {
                  type: 'string',
                  title: 'string title',
                  label: 'string label',
                  help: 'some string help',
                  validators: [],
                  input_hint: null,
                  autocompleter: null,
                  field_size: 'SMALL'
                } as String
              }
            ],
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
      i18n: defaultI18n
    }
  })

  // form is rendered correctly
  const stringInput = await screen.findByRole<HTMLInputElement>('textbox', { name: /string label/ })

  // data of form is visible in form
  expect(stringInput.value).toBe('some_data null')
})

// When fetch is aborted (component unmounted mid-flight), the real fetch() call rejects with a
// DOMException("AbortError") — a thrown exception, not an {error} return value. The try/catch in
// reloadAll catches it, checks signal.aborted, and returns silently so no error surfaces.
test('abort during fetch is silently suppressed on unmount', async () => {
  type Data = Record<string, unknown>
  const errorHandler = vi.fn()

  const { unmount } = render(FormSingleChoiceEditableEditAsync<string, Data>, {
    global: { config: { errorHandler } },
    props: {
      objectId: null,
      api: {
        getSchema: (_signal?: AbortSignal): Promise<FormSpec> =>
          new Promise((_, reject) => {
            _signal?.addEventListener('abort', () =>
              reject(new DOMException('The user aborted a request.', 'AbortError'))
            )
          }),
        getData: (_objectId: string | null, _signal?: AbortSignal): Promise<Data> =>
          new Promise((_, reject) => {
            _signal?.addEventListener('abort', () =>
              reject(new DOMException('The user aborted a request.', 'AbortError'))
            )
          }),
        setData: async (): Promise<SetDataResult<Data>> => ({ type: 'success', entity: {} })
      },
      i18n: defaultI18n
    }
  })

  unmount() // triggers abortController.abort() via onUnmounted
  await flushPromises()

  expect(errorHandler).not.toHaveBeenCalled()
})

// Non-abort errors (e.g. network failures, server errors) must still propagate so they are
// visible to the user — the catch block only swallows AbortErrors.
test('non-abort error from fetch is propagated', async () => {
  type Data = Record<string, unknown>
  const errorHandler = vi.fn()
  const networkError = new Error('network failure')

  render(FormSingleChoiceEditableEditAsync<string, Data>, {
    global: { config: { errorHandler } },
    props: {
      objectId: null,
      api: {
        getSchema: async (): Promise<FormSpec> => {
          throw networkError
        },
        getData: async (): Promise<Data> => ({}),
        setData: async (): Promise<SetDataResult<Data>> => ({ type: 'success', entity: {} })
      },
      i18n: defaultI18n
    }
  })

  await flushPromises()

  expect(errorHandler).toHaveBeenCalledWith(networkError, expect.anything(), expect.anything())
})
