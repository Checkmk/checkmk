/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'

/** Both ends of a kind of relation, by its id: "Management board and OS host". */
export function usePairNoun(relationNouns: () => Record<string, string>): (kind: string) => string {
  const { _t } = usei18n()
  return (kind) => {
    const nouns = relationNouns()
    const parent = nouns[`${kind}_parent`]
    const child = nouns[`${kind}_child`]
    if (parent !== undefined && child !== undefined) {
      return _t('%{parent} and %{child}', { parent, child })
    }
    return nouns[`${kind}_symmetric`] ?? kind
  }
}
