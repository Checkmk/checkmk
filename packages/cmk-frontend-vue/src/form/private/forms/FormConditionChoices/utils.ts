/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ConditionChoicesValue } from 'cmk-shared-typing/typescript/vue_formspec_components'

type KeysOfUnion<T> = T extends T ? keyof T : never
export type Operator = KeysOfUnion<ConditionChoicesValue['value']>

export type OperatorI18n = {
  choose_operator: string
  choose_condition: string
  eq_operator: string
  ne_operator: string
  or_operator: string
  nor_operator: string
}

export function translateOperator(i18n: OperatorI18n, operator: Operator): string {
  switch (operator) {
    case 'oper_eq':
      return i18n.eq_operator
    case 'oper_ne':
      return i18n.ne_operator
    case 'oper_or':
      return i18n.or_operator
    case 'oper_nor':
      return i18n.nor_operator
  }
}
