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

/** A plain entry, or the two halves of a `key: value` label, for its value to stand out. */
export type LabelCellItem = LabelCellStyle &
  ({ text: TranslatedString } | { keyValue: { key: string; value: string } })

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
