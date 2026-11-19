/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { AttributeKind } from 'cmk-shared-typing/typescript/attribute_filter'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { Metric, MetricMetadata } from './TimeSeriesGraph'

export type MetricAttribute = NonNullable<MetricMetadata['attributes']>[number]

export interface AttributeGroup {
  kind: string
  attributes: MetricAttribute[]
}

const KIND_RANKS: Record<AttributeKind, number> = { resource: 0, scope: 1, data_point: 2 }

function isAttributeKind(kind: string): kind is AttributeKind {
  return Object.hasOwn(KIND_RANKS, kind)
}

export function attributesOf(metric: Metric): MetricAttribute[] {
  return metric.metadata.attributes ?? []
}

/** Only OpenTelemetry metrics series carry attributes. */
export function hasAttributes(metric: Metric): boolean {
  return attributesOf(metric).length > 0
}

/** Sorted here so the presentation does not depend on the fetch layer's grouping. */
export function sortedAttributes(attributes: MetricAttribute[]): MetricAttribute[] {
  return [...attributes].sort((left, right) => kindRank(left.kind) - kindRank(right.kind))
}

function kindRank(kind: string): number {
  return isAttributeKind(kind) ? KIND_RANKS[kind] : Object.keys(KIND_RANKS).length
}

export function groupedAttributes(attributes: MetricAttribute[]): AttributeGroup[] {
  const groups = new Map<string, MetricAttribute[]>()
  for (const attribute of sortedAttributes(attributes)) {
    const group = groups.get(attribute.kind)
    if (group === undefined) {
      groups.set(attribute.kind, [attribute])
    } else {
      group.push(attribute)
    }
  }
  return [...groups].map(([kind, ofKind]) => ({ kind, attributes: ofKind }))
}

/** The "Attribute kind" column; an unknown kind is named raw rather than dropped. */
export function attributeKindColumnLabel(kind: string): string {
  const { _t } = usei18n()
  const labels: Record<AttributeKind, TranslatedString> = {
    resource: _t('Resource'),
    scope: _t('Scope'),
    data_point: _t('Data point')
  }
  return isAttributeKind(kind) ? labels[kind] : kind
}

/** The headings of the grouped rendering. */
export function attributeGroupTitle(kind: string): string {
  const { _t } = usei18n()
  const titles: Record<AttributeKind, TranslatedString> = {
    resource: _t('Resource attributes'),
    scope: _t('Scope attributes'),
    data_point: _t('Data point attributes')
  }
  return isAttributeKind(kind) ? titles[kind] : kind
}
