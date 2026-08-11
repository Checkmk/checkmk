/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'

export type HostsRequestBody = components['schemas']['HostsRequestBody']

export type HostsResponse = components['schemas']['HostsResponse']

export type HostEntry = components['schemas']['HostEntry']

export type HostOptionalField = components['schemas']['HostOptionalField']

export type ServiceOptionalField = components['schemas']['ServiceOptionalField']

export type HostServicesResponse = components['schemas']['HostServicesResponse']

export type HostServiceEntry = components['schemas']['HostServiceEntry']

export type ServicesRequestBody = components['schemas']['ServicesRequestBody']

/**
 * Boolean filter expression tree for the host services listing. Structurally shaped like
 * {@link FilterNode}, but scoped to whatever fields the service's own generated schema
 * defines, which is why it is kept as its own type rather than reusing the host one.
 */
export type ServiceFilterNode = components['schemas']['ServiceFilterNode']

export type HostOverview = components['schemas']['HostOverviewResponse']

export type ServiceOverview = components['schemas']['ServiceOverviewResponse']

export type HostMode = components['schemas']['ModeInfo']

export type ServiceMode = components['schemas']['ServiceModeInfo']

export type Perfometer = components['schemas']['ServicePerfometer']

export type HostLabelValue = components['schemas']['HostLabelValue']

export type ServiceLabelValue = components['schemas']['ServiceLabelValue']

/** Host and service labels carry the same shape today; the union keeps a future divergence a type error. */
export type LabelValue = HostLabelValue | ServiceLabelValue

export type ActionMenuItem = components['schemas']['ActionMenuItem']

export interface HostRef {
  site_id: string
  name: string
}

export interface ServiceRef {
  host: HostRef
  description: string
}

export type HostState = components['schemas']['HostState']

export type ServiceState = components['schemas']['ServiceStateLabel']

export type HostsPageMeta = components['schemas']['HostsPageMeta']

// --- Filter model ---------------------------------------------------------
// Two tree shapes share the same per-field conditions below:
//   - FilterNode: the whole-query tree (FilterStore's canonical representation), mixing
//     conditions on any field.
//   - ColumnFilterNode<F>: a single column funnel's tree, restricted to field F alone.
// Every field's condition shape is read straight off the generated schemas — host fields from
// `ConditionNode`, service fields (including service-only ones like `summary`) from
// `ServiceConditionNode` — so a new field on either side needs no type hand-written here.

/** The host's own generated filter condition schema. */
type HostConditionNode = components['schemas']['ConditionNode']

/** The service's own generated filter condition schema — covers fields with no host counterpart. */
type ServiceConditionNode = components['schemas']['ServiceConditionNode']

/** Every condition shape a field can resolve to, host or service. */
type AnyConditionNode = HostConditionNode | ServiceConditionNode

/** Every field a filter condition can target, across all monitoring pages. */
export type FilterField = AnyConditionNode['field']

/**
 * The condition shape(s) for field `F`. `C` must stay a naked type parameter (rather than being
 * substituted directly with `AnyConditionNode`) so the `extends` check distributes over the
 * union, picking out every member whose `field` matches `F` — e.g. `state` resolves to both the
 * host's and the service's state condition, since both schemas define that field.
 */
type ConditionForField<
  F extends FilterField,
  C extends AnyConditionNode = AnyConditionNode
> = C extends { field: infer Fields } ? (F extends Fields ? C : never) : never

/** Lookup table from field to its condition shape — the building block for both trees below. */
export type FieldConditionMap = {
  [F in FilterField]: ConditionForField<F>
}

/** Every condition a {@link FilterNode} can carry, across every field. */
export type ConditionNode = FieldConditionMap[FilterField]

export type NumericCondition = Extract<ConditionNode, { value: number }>

export type NumericOp = NumericCondition['op']

/**
 * Boolean filter expression tree: the whole query's conditions, mixing any fields. Recursively
 * defined from {@link ConditionNode} rather than a straight alias of the generated schema type,
 * so it can carry service fields the host schema alone doesn't know about.
 */
export type FilterNode =
  | { type: 'and'; children: FilterNode[] }
  | { type: 'or'; children: FilterNode[] }
  | { type: 'not'; child: FilterNode }
  | ConditionNode

/** A single column funnel's tree: conditions restricted to one field, `F`. */
export type ColumnFilterNode<F extends FilterField> =
  | { type: 'and'; children: ColumnFilterNode<F>[] }
  | { type: 'or'; children: ColumnFilterNode<F>[] }
  | { type: 'not'; child: ColumnFilterNode<F> }
  | FieldConditionMap[F]
