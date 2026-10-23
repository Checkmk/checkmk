/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, screen } from '@testing-library/vue'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import { vi } from 'vitest'
import { nextTick } from 'vue'

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
      default_value: {
        input_html: '<input name="legacy_varprefix" />',
        varprefix: 'legacy_varprefix'
      },
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

function legacyEntry(varprefix: string, value = 'empty') {
  return {
    input_html: `<input name="${varprefix}_value" id="${varprefix}_value" value="${value}" />`,
    readonly_html: '',
    varprefix
  }
}

test('FormLegacyValueSpec list entries post their fields under distinct varprefixes', async () => {
  const listSpec: FormSpec.List = {
    type: 'list',
    title: 'Custom icons and actions',
    help: '',
    validators: [],
    element_template: {
      type: 'legacy_valuespec',
      title: '',
      help: '',
      validators: [],
      varprefix: 'template'
    } as FormSpec.LegacyValuespec,
    element_default_value: legacyEntry('template'),
    editable_order: false,
    add_element_label: 'Add element',
    remove_element_label: 'Remove element',
    no_element_label: 'No element'
  }
  const { getCurrentData } = await renderForm({
    spec: listSpec,
    data: [legacyEntry('from_disk')],
    backendValidation: []
  })

  await fireEvent.click(screen.getByText('Add element'))
  await fireEvent.click(screen.getByText('Add element'))

  const entries = JSON.parse(getCurrentData()!) as Array<{
    varprefix: string
    input_context: Record<string, string>
  }>
  expect(entries.map((entry) => Object.keys(entry.input_context))).toEqual(
    entries.map((entry) => [`${entry.varprefix}_value`])
  )
  expect(new Set(entries.map((entry) => entry.varprefix)).size).toBe(3)
})

const legacySpec: FormSpec.LegacyValuespec = {
  type: 'legacy_valuespec',
  title: 'Icon',
  help: '',
  validators: [],
  varprefix: 'template'
}

test('FormLegacyValueSpec posts its fields again after its data is reloaded unchanged', async () => {
  const { getCurrentData, rerender } = await renderForm({
    spec: legacySpec,
    data: legacyEntry('from_disk'),
    backendValidation: []
  })

  await rerender({ data: legacyEntry('reloaded') })

  const entry = JSON.parse(getCurrentData()!) as {
    varprefix: string
    input_context?: Record<string, string>
  }
  expect(Object.keys(entry.input_context ?? {})).toEqual([`${entry.varprefix}_value`])
})

test('FormLegacyValueSpec posts the reloaded value after its data is replaced', async () => {
  const { getCurrentData, rerender } = await renderForm({
    spec: legacySpec,
    data: legacyEntry('from_disk'),
    backendValidation: []
  })

  await rerender({ data: legacyEntry('reloaded', 'access') })
  await nextTick()

  const entry = JSON.parse(getCurrentData()!) as {
    varprefix: string
    input_context?: Record<string, string>
  }
  expect(entry.input_context).toEqual({ [`${entry.varprefix}_value`]: 'access' })
})

test('FormLegacyValueSpec dispatches callable TS functions of the reloaded legacy HTML', async () => {
  const { container, rerender } = await renderForm({
    spec: legacySpec,
    data: legacyEntry('from_disk'),
    backendValidation: []
  })
  initCallableTsFunctions.mockClear()

  await rerender({ data: legacyEntry('reloaded', 'access') })
  await nextTick()

  const legacyForm = container.querySelector('.legacy_valuespec')
  expect(initCallableTsFunctions).toHaveBeenCalledWith(legacyForm)
})
