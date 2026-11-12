/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Colors, Variants } from 'cmk-ui-library/components/CmkTag.vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

interface LabelCellStyle {
  color?: Colors | undefined
  variant?: Variants | undefined
}

export interface TagPair {
  group: string
  value: string
}

export type TagItem = LabelCellStyle & { text: TranslatedString; tag: TagPair }

/** A plain entry, or the two halves of a `key: value` label, for its value to stand out. */
export type LabelCellItem =
  | (LabelCellStyle & ({ text: TranslatedString } | { keyValue: { key: string; value: string } }))
  | TagItem

/** What a click on an entry does; without one the entry is plain. */
export interface ItemAction {
  title: (item: LabelCellItem) => TranslatedString
  /** The page the entry links to; without it a click selects the entry. */
  href?: ((item: LabelCellItem) => string) | undefined
}

export function isTagItem(item: LabelCellItem): item is TagItem {
  return 'tag' in item
}

export function labelItemText(item: LabelCellItem): TranslatedString {
  return 'keyValue' in item
    ? (`${item.keyValue.key}: ${item.keyValue.value}` as TranslatedString)
    : item.text
}

/** What a tag shows before the value of a label set in bold: its key, or the whole entry. */
export function labelItemContent(item: LabelCellItem): TranslatedString {
  return 'keyValue' in item ? (item.keyValue.key as TranslatedString) : item.text
}

export function labelItemValue(item: LabelCellItem): string | undefined {
  return 'keyValue' in item ? item.keyValue.value : undefined
}
