/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, screen } from '@testing-library/vue'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import { vi } from 'vitest'

import { renderForm } from '../cmk-form-helper'

const initCallableTsFunctions = vi.fn()

beforeEach(() => {
  initCallableTsFunctions.mockClear()
  // @ts-expect-error comes from different javascript file
  window['cmk'] = {
    forms: { enable_dynamic_form_elements: () => {} },
    valuespecs: { initialize_autocompleters: () => {} },
    ts_function_dispatcher: { init_callable_ts_functions: initCallableTsFunctions }
  }
})

// Similar to "Certificate to sign requests (PEM)" from the SAML authentication page.
const spec: FormSpec.CascadingSingleChoice = {
  type: 'cascading_single_choice',
  title: 'Certificate to sign requests (PEM)',
  help: '',
  validators: [],
  no_elements_text: '(No choices available)',
  label: null,
  input_hint: null,
  layout: 'vertical',
  button_group_size: 'medium',
  elements: [
    {
      name: 'builtin',
      title: 'Use Checkmk certificate',
      default_value: true,
      parameter_form: {
        type: 'fixed_value',
        title: '',
        help: '',
        validators: [],
        label: '',
        value: true
      } as FormSpec.FixedValue
    },
    {
      name: 'custom',
      title: 'Use custom certificate',
      default_value: { input_html: '<input name="private_key" />' },
      parameter_form: {
        type: 'legacy_valuespec',
        title: '',
        help: '',
        validators: [],
        varprefix: 'legacy_varprefix'
      } as FormSpec.LegacyValuespec
    }
  ]
}

function legacyInputs(container: Element): NodeListOf<HTMLInputElement> {
  return container.querySelectorAll<HTMLInputElement>('.legacy_valuespec input')
}

async function selectChoice(name: string): Promise<void> {
  await fireEvent.click(screen.getByRole('combobox'))
  await fireEvent.click(await screen.findByText(name))
}

test('FormLegacyValueSpec toggling works', async () => {
  const { container } = await renderForm({
    spec,
    data: ['builtin', true],
    backendValidation: []
  })

  await selectChoice('Use custom certificate')
  expect(legacyInputs(container)).toHaveLength(1)

  await selectChoice('Use Checkmk certificate')
  expect(legacyInputs(container)).toHaveLength(0)

  await selectChoice('Use custom certificate')
  expect(legacyInputs(container)).toHaveLength(1)
})

test('FormLegacyValueSpec dispatches callable TS functions of the legacy HTML', async () => {
  const { container } = await renderForm({
    spec,
    data: ['builtin', true],
    backendValidation: []
  })

  await selectChoice('Use custom certificate')

  const legacyForm = container.querySelector('.legacy_valuespec')
  expect(initCallableTsFunctions).toHaveBeenCalledWith(legacyForm)
})
