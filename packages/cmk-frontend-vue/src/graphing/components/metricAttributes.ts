/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import {
  ATTRIBUTE_KIND_ORDER,
  type AttributeKind,
  attributeKindLabel
} from '@/metric-backend/attribute-kind'

import type { Metric, MetricMetadata } from './TimeSeriesGraph'

export type MetricAttribute = NonNullable<MetricMetadata['attributes']>[number]

export interface AttributeGroup {
  kind: string
  attributes: MetricAttribute[]
}

function isAttributeKind(kind: string): kind is AttributeKind {
  return ATTRIBUTE_KIND_ORDER.some((known) => known === kind)
}

export function attributesOf(metric: Metric): MetricAttribute[] {
  return metric.metadata.attributes ?? []
}

/** Only metrics-backend series carry attributes. */
export function hasAttributes(metric: Metric): boolean {
  return attributesOf(metric).length > 0
}

/** Sorted here so the presentation does not depend on the fetch layer's grouping. */
export function sortedAttributes(attributes: MetricAttribute[]): MetricAttribute[] {
  return [...attributes].sort((left, right) => kindRank(left.kind) - kindRank(right.kind))
}

function kindRank(kind: string): number {
  const rank = ATTRIBUTE_KIND_ORDER.findIndex((known) => known === kind)
  return rank === -1 ? ATTRIBUTE_KIND_ORDER.length : rank
}

export function groupedAttributes(attributes: MetricAttribute[]): AttributeGroup[] {
  const groups = new Map<string, MetricAttribute[]>(ATTRIBUTE_KIND_ORDER.map((kind) => [kind, []]))
  for (const attribute of attributes) {
    const group = groups.get(attribute.kind)
    if (group === undefined) {
      groups.set(attribute.kind, [attribute])
    } else {
      group.push(attribute)
    }
  }
  return [...groups]
    .filter(([, ofKind]) => ofKind.length > 0)
    .map(([kind, ofKind]) => ({ kind, attributes: ofKind }))
}

/** The "Attribute type" column; an unknown kind is named raw rather than dropped. */
export function attributeTypeLabel(kind: string): string {
  return isAttributeKind(kind) ? attributeKindLabel(kind) : kind
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
