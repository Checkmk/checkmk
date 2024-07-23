import { render } from '@testing-library/vue'
import CmkFormDataVisualizer from './CmkFormDataVisualizer.vue'
import type { FormSpec } from '@/vue_formspec_components'
import type { ValidationMessages } from '@/utils'

export function renderFormWithData(props: {
  spec: FormSpec
  data: unknown
  backendValidation: ValidationMessages
}) {
  const { container, ...renderResult } = render(CmkFormDataVisualizer, { props: props })

  const getCurrentData = () => container.querySelector('[data-testid=test-data]')?.textContent

  return { getCurrentData: getCurrentData, ...renderResult }
}
