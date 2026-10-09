/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Dictionary, FormSpec } from 'cmk-shared-typing/typescript/vue_formspec_components'

import type { ValidationMessages } from '@/form'
import { validateValue } from '@/form/private/validation'

function isDictionary(spec: FormSpec): spec is Dictionary {
  return (spec as { type?: string }).type === 'dictionary'
}

// Validate what the backend validates: it drops these empty entries on parsing first.
function parsedValue(spec: FormSpec, value: unknown): unknown {
  if (!Array.isArray(value)) {
    return value
  }
  switch ((spec as { type?: string }).type) {
    // The list always offers an empty entry to type into.
    case 'list_of_strings':
      return value.filter((entry) => entry !== '')
    case 'binary_condition_choices':
      return value.filter((group: { label_group: unknown[] }) => group.label_group.length > 0)
    default:
      return value
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

/**
 * The messages of the form spec's own validators for the whole value, located like backend
 * validation, so a step can show them all at once instead of only on the fields edited.
 */
export function formSpecErrors(
  spec: FormSpec,
  value: unknown,
  location: string[] = []
): ValidationMessages {
  // A field keeps its value: the form takes a message's replacement value as the new value.
  const own = validateValue(parsedValue(spec, value), spec.validators).map((message) => ({
    location,
    message,
    replacement_value: value
  }))
  if (!isDictionary(spec) || !isRecord(value)) {
    return own
  }
  return [
    ...own,
    ...spec.elements
      .filter((element) => element.name in value)
      .flatMap((element) =>
        formSpecErrors(element.parameter_form, value[element.name], [...location, element.name])
      )
  ]
}
