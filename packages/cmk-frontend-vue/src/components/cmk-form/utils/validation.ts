import { ref, watch, type Ref, computed, type WritableComputedRef } from 'vue'
import { validateValue, type ValidationMessages } from '@/lib/validation'
import type { Validator } from '@/vue_formspec_components'

/**
 * Hook to handle validation messages and update date if invalid value is provided
 */
export function useValidation<Type>(
  data: Ref<Type | string>,
  validators: Validator[],
  getBackendValidation: () => ValidationMessages
): [Ref<ValidationMessages>, WritableComputedRef<Type | string>] {
  const validation = ref<ValidationMessages>([])

  watch(
    getBackendValidation,
    (newValidation: ValidationMessages) => {
      newValidation.forEach((message) => {
        data.value = message.invalid_value as string
      })
      validation.value = newValidation
    },
    { immediate: true }
  )

  const value = computed<Type | string>({
    get() {
      return data.value
    },
    set(value: Type | string) {
      validation.value = []
      validateValue(value, validators).forEach((error) => {
        validation.value = [{ message: error, location: [], invalid_value: value }]
      })
      data.value = value
    }
  })
  return [validation, value]
}
