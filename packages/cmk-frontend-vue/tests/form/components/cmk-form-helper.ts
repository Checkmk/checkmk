/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type RenderResult, render } from '@testing-library/vue'
import type { FormSpec } from 'cmk-shared-typing/typescript/vue_formspec_components'

import type { ValidationMessages } from '@/form/private/validation'

import FormDataVisualizer from './FormDataVisualizer.vue'

export async function renderForm(props: {
  spec: FormSpec
  data: unknown
  backendValidation: ValidationMessages
}): Promise<RenderResult & { getCurrentData: () => string | null | undefined }> {
  const { container, ...renderResult } = render(FormDataVisualizer, { props: props })

  await vi.dynamicImportSettled()

  const getCurrentData = () => container.querySelector('[id=test-data]')?.textContent

  return { getCurrentData: getCurrentData, container, ...renderResult }
}
