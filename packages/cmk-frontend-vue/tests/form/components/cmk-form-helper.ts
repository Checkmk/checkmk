import { render } from '@testing-library/vue'
import FormDataVisualizer from './FormDataVisualizer.vue'
import type { FormSpec } from '@/vue_formspec_components'
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
