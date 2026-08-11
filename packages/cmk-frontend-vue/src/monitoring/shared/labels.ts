/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Colors } from 'cmk-ui-library/components/CmkTag.vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { LabelValue } from '@/monitoring/shared/api/types'
import type { LabelCellItem } from '@/monitoring/shared/components/cell/LabelCell.vue'

const SOURCE_COLORS: Record<string, Colors> = {
  discovered: 'discovered',
  explicit: 'explicit',
  ruleset: 'ruleset'
}

export function labelColor(source: string): Colors {
  return SOURCE_COLORS[source] ?? 'default'
}

/** Order entries alphabetically, so a row reads the same on every refresh. */
function sortedByText(items: LabelCellItem[]): LabelCellItem[] {
  return items.sort((first, second) => first.text.localeCompare(second.text))
}

/**
 * Render labels as `key: value` entries, colored by the source they were set from and ordered
 * alphabetically so a row reads the same on every refresh.
 */
export function toLabelItems(labels: Record<string, LabelValue>): LabelCellItem[] {
  return sortedByText(
    Object.entries(labels).map(([key, label]) => ({
      text: `${key}: ${label.value}` as TranslatedString,
      color: labelColor(label.source)
    }))
  )
}

/** Render plain names, e.g. contact groups, as entries. */
export function toNameItems(names: string[]): LabelCellItem[] {
  return sortedByText(names.map((name) => ({ text: name as TranslatedString })))
}

/**
 * Render tags as `group: value` entries. Tags have no source to distinguish, so they all carry
 * the same color.
 */
export function toTagItems(tags: Record<string, string>): LabelCellItem[] {
  return sortedByText(
    Object.entries(tags).map(([group, value]) => ({
      text: `${group}: ${value}` as TranslatedString
    }))
  )
}
