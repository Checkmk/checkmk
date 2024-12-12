/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import FormDataSize from '@/form/components/forms/FormDataSize.vue'

const spec: FormSpec.DataSize = {
  type: 'data_size',
  title: 'fooTitle',
  help: 'fooHelp',
  displayed_magnitudes: ['mag_foo', 'mag_bar'],
  validators: [],
  label: 'fooLabel',
  input_hint: 'fooInputHint'
}

test('FormDataSize renders value', () => {
  render(FormDataSize, {
    props: {
      spec,
      data: ['42', 'mag_bar'],
      backendValidation: []
    }
  })

  const inputElement = screen.getByRole<HTMLInputElement>('spinbutton', { name: 'fooLabel' })
  const selectElement = screen.getByRole<HTMLInputElement>('combobox')

  expect(inputElement.value).toBe('42')
  expect(selectElement).toHaveAccessibleName('mag_bar')
})
