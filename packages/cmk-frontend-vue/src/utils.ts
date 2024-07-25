/**
 * Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import type { DictionaryElement, ValidationMessage, Validators } from '@/vue_formspec_components'

export function validate_value(new_value: unknown, validators: Validators[]): string[] {
  const errors: string[] = []
  for (const validator of validators) {
    if (validator.type === 'length_in_range') {
      const check_value = new_value as Array<unknown>
      const min_value = validator.min_value
      const max_value = validator.max_value
      if (min_value !== null && min_value !== undefined && check_value.length < min_value) {
        errors.push(validator.error_message!)
      }
      if (max_value !== null && max_value !== undefined && check_value.length > max_value) {
        errors.push(validator.error_message!)
      }
    } else if (validator.type === 'number_in_range') {
      const check_value = new_value as number
      const min_value = validator.min_value
      const max_value = validator.max_value
      if (min_value !== null && min_value !== undefined && check_value < min_value) {
        errors.push(validator.error_message!)
      }
      if (max_value !== null && max_value !== undefined && check_value > max_value) {
        errors.push(validator.error_message!)
      }
    } else if (validator.type === 'is_integer') {
      const check_value = new_value as string
      if (!is_integer(check_value)) {
        errors.push(validator.error_message!)
      }
    } else if (validator.type === 'is_float') {
      const check_value = new_value as string
      if (!is_float(check_value)) {
        errors.push(validator.error_message!)
      }
    }
  }
  return errors
}

export function is_integer(value: string): boolean {
  return /^-?\d+$/.test(value)
}

export function is_float(value: string): boolean {
  return /^-?\d+\.?\d+$/.test(value)
}

export type ValidationMessages = ValidationMessage[]

export function group_dictionary_validations(
  elements: DictionaryElement[],
  new_validation: ValidationMessages
): [ValidationMessages, Record<string, ValidationMessages>] {
  // Prepare all elements with an empty list of validation messages
  const element_validations = elements.reduce(
    (elements, el) => {
      elements[el.ident] = []
      return elements
    },
    {} as Record<string, ValidationMessages>
  )
  const dictionary_validations: ValidationMessages = []

  new_validation.forEach((msg) => {
    if (msg.location.length == 0) {
      dictionary_validations.push(msg)
      return
    }
    const msg_element_ident = msg.location[0]!
    const element_messages = element_validations[msg_element_ident]
    if (element_messages === undefined) {
      throw new Error(`Index ${msg_element_ident} not found in dictionary`)
    }
    element_messages.push({
      location: msg.location.slice(1),
      message: msg.message,
      invalid_value: msg.invalid_value
    })
    element_validations[msg_element_ident] = element_messages
  })
  return [dictionary_validations, element_validations]
}

export function group_list_validations(
  messages: ValidationMessages,
  number_of_elements: number
): [ValidationMessages, Record<number, ValidationMessages>] {
  const list_validations: ValidationMessages = []
  const element_validations: Record<number, ValidationMessages> = []
  // This functions groups the validation messages by the index of the element they belong to
  // Initialize the array with empty arrays
  for (let i = 0; i < number_of_elements; i++) {
    element_validations[i] = []
  }
  messages.forEach((msg) => {
    const index = msg.location.length == 0 ? -1 : parseInt(msg.location[0]!)
    if (index == -1) {
      list_validations.push(msg)
      return
    }
    const element_messages = element_validations[index] || []
    element_messages.push({
      location: msg.location.slice(1),
      message: msg.message,
      invalid_value: msg.invalid_value
    })
    element_validations[index] = element_messages
  })
  return [list_validations, element_validations]
}
