/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { computed, ref, type Ref, type WritableComputedRef } from 'vue'
import type {
  ValidationMessage,
  Validator
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import { immediateWatch } from '@/lib/watch'

/**
 * Hook to handle validation messages and update date if invalid value is provided
 */
export type ValidationMessages = ValidationMessage[]

export function useValidation<Type>(
  data: Ref<Type>,
  validators: Validator[],
  getBackendValidation: () => ValidationMessages
): [Ref<Array<string>>, WritableComputedRef<Type>] {
  const validation = ref<Array<string>>([])

  immediateWatch(getBackendValidation, (newValidation: ValidationMessages) => {
    validation.value = newValidation.map((m) => m.message)
    newValidation.forEach((message) => {
      data.value = message.replacement_value as Type
    })
  })

  const value = computed<Type>({
    get() {
      return data.value
    },
    set(value: Type) {
      validation.value = validateValue(value, validators)
      data.value = value
    }
  })
  return [validation, value]
}

export function validateValue(newValue: unknown, validators: Validator[]): string[] {
  const errors: string[] = []
  for (const validator of validators) {
    if (validator.type === 'length_in_range') {
      const checkValue = newValue as Array<unknown>
      const minValue = validator.min_value
      const maxValue = validator.max_value
      if (minValue !== null && checkValue.length < minValue) {
        errors.push(validator.error_message!)
      }
      if (maxValue !== null && checkValue.length > maxValue) {
        errors.push(validator.error_message!)
      }
    } else if (validator.type === 'number_in_range') {
      const checkValue = newValue as number
      const minValue = validator.min_value
      const maxValue = validator.max_value
      if (minValue !== null && checkValue < minValue) {
        errors.push(validator.error_message!)
      }
      if (maxValue !== null && checkValue > maxValue) {
        errors.push(validator.error_message!)
      }
    } else if (validator.type === 'is_integer') {
      if (!isInteger(newValue)) {
        errors.push(validator.error_message!)
      }
    } else if (validator.type === 'is_float') {
      const checkValue = newValue as string
      if (!isFloat(checkValue)) {
        errors.push(validator.error_message!)
      }
    }
  }
  return errors
}

export function isInteger(value: unknown): boolean {
  if (typeof value !== 'number') {
    return false
  }
  return Number.isInteger(value)
}

export function isFloat(value: string): boolean {
  return /^-?\d+(\.\d+)?$/.test(value)
}

export function requiresSomeInput(validators: Validator[]): boolean {
  return validators.some((validator) => {
    if (validator.type === 'length_in_range') {
      if (validator.min_value === null) {
        return false
      }
      return validator.min_value > 0
    }
    return false
  })
}

export function groupNestedValidations(
  elements: Array<{ name: string }>,
  newValidation: ValidationMessages
): [ValidationMessages, Record<string, ValidationMessages>] {
  // Prepare all elements with an empty list of validation messages
  const elementValidations = elements.reduce(
    (elements, el) => {
      elements[el.name] = []
      return elements
    },
    {} as Record<string, ValidationMessages>
  )
  const dictionaryValidations: ValidationMessages = []

  newValidation.forEach((msg) => {
    if (msg.location.length === 0) {
      dictionaryValidations.push(msg)
      return
    }
    const msgElementIdent = msg.location[0]!
    const elementMessages = elementValidations[msgElementIdent]
    if (elementMessages === undefined) {
      throw new Error(`Index ${msgElementIdent} not found in dictionary`)
    }
    elementMessages.push({
      location: msg.location.slice(1),
      message: msg.message,
      replacement_value: msg.replacement_value
    })
    elementValidations[msgElementIdent] = elementMessages
  })
  return [dictionaryValidations, elementValidations]
}

export function groupIndexedValidations(
  messages: ValidationMessages,
  numberOfElements: number
): [Array<string>, Record<number, ValidationMessages>] {
  const ownValidations: Array<string> = []
  const elementValidations: Record<number, ValidationMessages> = []
  // This functions groups the validation messages by the index of the element they belong to
  // Initialize the array with empty arrays
  for (let i = 0; i < numberOfElements; i++) {
    elementValidations[i] = []
  }
  messages.forEach((msg) => {
    const index = msg.location.length === 0 ? -1 : parseInt(msg.location[0]!)
    if (index === -1) {
      ownValidations.push(msg.message)
      return
    }
    const elementMessages = elementValidations[index] || []
    elementMessages.push({
      location: msg.location.slice(1),
      message: msg.message,
      replacement_value: msg.replacement_value
    })
    elementValidations[index] = elementMessages
  })
  return [ownValidations, elementValidations]
}
