import { render } from '@testing-library/vue'
import CmkFormDataVisualizer from './CmkFormDataVisualizer.vue'
import type { FormSpec } from '@/vue_formspec_components'

export function renderFormWithData(props: { spec: FormSpec; data: unknown }) {
  const { container, ...renderResult } = render(CmkFormDataVisualizer, { props: props })

  const getCurrentData = () => container.querySelector('[data-testid=test-data]')?.textContent

  return { getCurrentData: getCurrentData, ...renderResult }
}
