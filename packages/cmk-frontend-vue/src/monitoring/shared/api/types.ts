/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'

export type HostsRequestBody = components['schemas']['HostsRequestBody']

export type HostsResponse = components['schemas']['HostsResponse']

export type HostEntry = components['schemas']['HostEntry']

export type HostState = components['schemas']['HostState']

export type HostsPageMeta = components['schemas']['HostsPageMeta']

export type FilterNode = components['schemas']['FilterNode']

export type ConditionNode = components['schemas']['ConditionNode']

export type FilterField = ConditionNode['field']

export type NumericCondition = Extract<ConditionNode, { value: number }>

export type NumericOp = NumericCondition['op']

type ConditionForField<F extends FilterField, C extends ConditionNode = ConditionNode> = C extends {
  field: infer Fields
}
  ? F extends Fields
    ? C
    : never
  : never

export type FieldConditionMap = {
  [F in FilterField]: ConditionForField<F>
}

export type ColumnFilterNode<F extends FilterField> =
  | { type: 'and'; children: ColumnFilterNode<F>[] }
  | { type: 'or'; children: ColumnFilterNode<F>[] }
  | { type: 'not'; child: ColumnFilterNode<F> }
  | FieldConditionMap[F]
