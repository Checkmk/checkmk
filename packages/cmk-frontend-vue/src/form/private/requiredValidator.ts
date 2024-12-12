/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Validator } from 'cmk-shared-typing/typescript/vue_formspec_components'

export default function required(validator: Validator): boolean {
  return (
    (validator.type === 'length_in_range' &&
      validator.min_value !== null &&
      validator.min_value > 0) ||
    (validator.type === 'number_in_range' &&
      validator.min_value !== null &&
      validator.min_value > 0)
  )
}
