import { ref, watch, type Ref } from 'vue'
import type { ValidationMessages } from '@/lib/validation'

/**
 * Hook to handle validation messages and update date if invalid value is provided
 */
export function useValidation<Type>(
  data: Ref<Type | string>,
  getBackendValidation: () => ValidationMessages
): Ref<ValidationMessages> {
  const validation = ref<ValidationMessages>([])

  watch(
    getBackendValidation,
    (new_validation: ValidationMessages) => {
      new_validation.forEach((message) => {
        data.value = message.invalid_value as string
      })
      validation.value = new_validation
    },
    { immediate: true }
  )

  return validation
}
