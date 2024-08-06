import type { DictionaryElement, ValidationMessage, Validators } from '@/vue_formspec_components'

export function validateValue(newValue: unknown, validators: Validators[]): string[] {
  const errors: string[] = []
  for (const validator of validators) {
    if (validator.type === 'length_in_range') {
      const checkValue = newValue as Array<unknown>
      const minValue = validator.min_value
      const maxValue = validator.max_value
      if (minValue !== null && minValue !== undefined && checkValue.length < minValue) {
        errors.push(validator.error_message!)
      }
      if (maxValue !== null && maxValue !== undefined && checkValue.length > maxValue) {
        errors.push(validator.error_message!)
      }
    } else if (validator.type === 'number_in_range') {
      const checkValue = newValue as number
      const minValue = validator.min_value
      const maxValue = validator.max_value
      if (minValue !== null && minValue !== undefined && checkValue < minValue) {
        errors.push(validator.error_message!)
      }
      if (maxValue !== null && maxValue !== undefined && checkValue > maxValue) {
        errors.push(validator.error_message!)
      }
    } else if (validator.type === 'is_integer') {
      const checkValue = newValue as string
      if (!isInteger(checkValue)) {
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

export function isInteger(value: string): boolean {
  return /^-?\d+$/.test(value)
}

export function isFloat(value: string): boolean {
  return /^-?\d+(\.\d+)?$/.test(value)
}

export type ValidationMessages = ValidationMessage[]

export function groupDictionaryValidations(
  elements: DictionaryElement[],
  newValidation: ValidationMessages
): [ValidationMessages, Record<string, ValidationMessages>] {
  // Prepare all elements with an empty list of validation messages
  const elementValidations = elements.reduce(
    (elements, el) => {
      elements[el.ident] = []
      return elements
    },
    {} as Record<string, ValidationMessages>
  )
  const dictionaryValidations: ValidationMessages = []

  newValidation.forEach((msg) => {
    if (msg.location.length == 0) {
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
      invalid_value: msg.invalid_value
    })
    elementValidations[msgElementIdent] = elementMessages
  })
  return [dictionaryValidations, elementValidations]
}

export function groupListValidations(
  messages: ValidationMessages,
  numberOfElements: number
): [ValidationMessages, Record<number, ValidationMessages>] {
  const listValidations: ValidationMessages = []
  const elementValidations: Record<number, ValidationMessages> = []
  // This functions groups the validation messages by the index of the element they belong to
  // Initialize the array with empty arrays
  for (let i = 0; i < numberOfElements; i++) {
    elementValidations[i] = []
  }
  messages.forEach((msg) => {
    const index = msg.location.length == 0 ? -1 : parseInt(msg.location[0]!)
    if (index == -1) {
      listValidations.push(msg)
      return
    }
    const elementMessages = elementValidations[index] || []
    elementMessages.push({
      location: msg.location.slice(1),
      message: msg.message,
      invalid_value: msg.invalid_value
    })
    elementValidations[index] = elementMessages
  })
  return [listValidations, elementValidations]
}
