/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import FormDataVisualizer from './FormDataVisualizer.vue'
import type { FormSpec } from 'cmk-shared-typing/typescript/vue_formspec_components'
import type { ValidationMessages } from '@/form/components/utils/validation'

export function renderFormWithData(props: {
  spec: FormSpec
  data: unknown
  backendValidation: ValidationMessages
}) {
  const { container, ...renderResult } = render(FormDataVisualizer, { props: props })

  const getCurrentData = () => container.querySelector('[data-testid=test-data]')?.textContent

  return { getCurrentData: getCurrentData, ...renderResult }
}
