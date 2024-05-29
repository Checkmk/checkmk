/**
 * Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import * as d3 from 'd3'
import type { VueValidators1 } from '@/vue_validators'

export function clicked_checkbox_label(target: HTMLLabelElement) {
  // TODO: Better use the <label for="id"> mechanic instead of this workaround
  const parent_node = target.parentNode
  if (parent_node == null) {
    return
  }
  const bound_input_field = d3
    .select(parent_node as HTMLSpanElement)
    .select<HTMLInputElement>('input')

  if (bound_input_field.empty()) {
    return
  }
  bound_input_field.node()!.click()
}

export function validate_value(new_value: unknown, validators: VueValidators1[]): string[] {
  const errors: string[] = []
  for (const validator of validators) {
    if (validator.vue_type === 'length_in_range') {
      const check_value = new_value as Array<unknown>
      const min_value = validator.min_value
      const max_value = validator.max_value
      if (min_value !== null && min_value !== undefined && check_value.length < min_value)
        errors.push(validator.error_message!)
      if (max_value !== null && max_value !== undefined && check_value.length > max_value)
        errors.push(validator.error_message!)
    } else if (validator.vue_type === 'number_in_range') {
      const check_value = new_value as number
      const min_value = validator.min_value
      const max_value = validator.max_value
      if (min_value !== null && min_value !== undefined && check_value < min_value)
        errors.push(validator.error_message!)
      if (max_value !== null && max_value !== undefined && check_value > max_value)
        errors.push(validator.error_message!)
    } else if (validator.vue_type === 'is_integer') {
      const check_value = new_value as string
      if (!is_integer(check_value)) errors.push(validator.error_message!)
    } else if (validator.vue_type === 'is_float') {
      const check_value = new_value as string
      if (!is_float(check_value)) errors.push(validator.error_message!)
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

export interface ValidationMessage {
  location: string[]
  message: string
}
export type ValidationMessages = ValidationMessage[]
