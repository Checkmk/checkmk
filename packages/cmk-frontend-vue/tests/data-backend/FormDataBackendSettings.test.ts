/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import { restApiHttp, useMswServer } from 'cmk-ui-library/vitest.msw'

import FormReadonly from '@/form/FormReadonly.vue'

import { registerDataBackendFormComponents } from '@/data-backend/registerFormComponents'

import { renderForm } from '../form/components/cmk-form-helper'

registerDataBackendFormComponents()

const server = useMswServer()

const CENTRAL = 'encoded-central'
const DISABLED = 'encoded-disabled'
const ADDRESS_TITLE = 'Address this site connects to the central data backend from'

function dictionaryElement(name: string, parameterForm: FormSpec.FormSpec, defaultValue: unknown) {
  return {
    name,
    required: true,
    group: null,
    default_value: defaultValue,
    render_only: false,
    parameter_form: parameterForm
  }
}

const telemetryLocationChoice: FormSpec.SingleChoice = {
  type: 'single_choice',
  title: 'OpenTelemetry metrics',
  help: '',
  validators: [],
  elements: [
    { name: CENTRAL, title: 'Central data backend' },
    { name: DISABLED, title: 'Disabled' }
  ],
  no_elements_text: null,
  frozen: false,
  label: null,
  input_hint: null
}

const features: FormSpec.Dictionary = {
  type: 'dictionary',
  title: 'Data backend used by each feature',
  help: '',
  validators: [],
  elements: [dictionaryElement('telemetry', telemetryLocationChoice, DISABLED)],
  groups: [],
  no_elements_text: '',
  additional_static_elements: null
}

const address: FormSpec.String = {
  type: 'string',
  title: ADDRESS_TITLE,
  help: '',
  validators: [],
  label: null,
  input_hint: null,
  field_size: 'medium',
  autocompleter: null
}

const spec: FormSpec.DataBackendSettings = {
  type: 'data_backend_settings',
  title: 'Data backend',
  help: '',
  validators: [],
  elements: [
    dictionaryElement('features', features, { telemetry: DISABLED }),
    dictionaryElement('address_seen_by_central', address, '')
  ],
  groups: [],
  no_elements_text: '',
  additional_static_elements: null,
  central_location: CENTRAL,
  connection_test_site_id: null
}
const remoteSpec: FormSpec.DataBackendSettings = { ...spec, connection_test_site_id: 'remote1' }

test('shows the address only while a feature uses the central data backend', async () => {
  await renderForm({
    spec,
    data: { features: { telemetry: DISABLED } },
    backendValidation: []
  })
  expect(screen.queryByRole('textbox', { name: ADDRESS_TITLE })).toBeNull()

  await userEvent.click(screen.getByRole('combobox', { name: 'OpenTelemetry metrics' }))
  await userEvent.click(screen.getByRole('option', { name: 'Central data backend' }))

  expect(await screen.findByRole('textbox', { name: ADDRESS_TITLE })).toBeVisible()
})

test('shows the backend validation of the address at the address', async () => {
  await renderForm({
    spec,
    data: { features: { telemetry: CENTRAL }, address_seen_by_central: '' },
    backendValidation: [
      { location: ['address_seen_by_central'], message: 'Address missing', replacement_value: '' }
    ]
  })

  expect(screen.getByRole('group', { name: ADDRESS_TITLE })).toHaveTextContent('Address missing')
})

test.each([
  { location: DISABLED, shownAddresses: 0 },
  { location: CENTRAL, shownAddresses: 1 }
])(
  'readonly view shows the address only while a feature uses the central data backend ($location)',
  ({ location, shownAddresses }) => {
    render(FormReadonly, {
      props: {
        spec,
        data: { features: { telemetry: location }, address_seen_by_central: '10.0.0.2' },
        backendValidation: []
      }
    })

    expect(screen.queryAllByText('10.0.0.2')).toHaveLength(shownAddresses)
  }
)

test('the connection test sends the settings as entered', async () => {
  let requestBody: unknown
  server.use(
    restApiHttp.post(
      '/domain-types/data_backend/actions/test_central_connection/invoke',
      async ({ request, response }) => {
        requestBody = await request.json()
        return response(200).json({ running: false, phases: [] })
      }
    ),
    restApiHttp.get(
      '/domain-types/data_backend/actions/show_central_connection_test/invoke',
      ({ response }) => response(200).json({ running: false, phases: [] })
    )
  )
  await renderForm({
    spec: remoteSpec,
    data: { features: { telemetry: CENTRAL }, address_seen_by_central: '10.0.0.2' },
    backendValidation: []
  })

  await userEvent.type(screen.getByRole('textbox', { name: ADDRESS_TITLE }), '0')
  await userEvent.click(screen.getByRole('button', { name: 'Test connection' }))

  await waitFor(() =>
    expect(requestBody).toEqual({
      site_id: 'remote1',
      centrally_routed_features: ['telemetry'],
      address_seen_by_central: '10.0.0.20',
      allow_restart: false
    })
  )
})
