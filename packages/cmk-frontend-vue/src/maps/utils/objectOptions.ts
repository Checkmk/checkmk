/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Object-option registry — the canonical names of line styles (and, later, other
 * per-object choice kinds).
 *
 * This is a STATIC frontend catalogue: the names are a fixed UI vocabulary, so
 * there is no config and no fetch. Display titles are resolved from the i18n
 * catalogue keyed by ``name`` (see ``utils/dropdownOptions.ts``); the ``title``
 * here is only an English fallback for a name without a translation.
 */
/** One selectable option: the stored name and its English fallback title. */
export interface ObjectOption {
  name: string
  title: string
}

// The fixed line-style vocabulary the renderer understands.
export const LINE_STYLES: ObjectOption[] = [
  { name: 'plain', title: 'Simple line' },
  { name: 'dashed', title: 'Dashed' },
  { name: 'arrow_end', title: 'Arrow at end' },
  { name: 'arrow_start', title: 'Arrow at start' },
  { name: 'arrow_both', title: 'Arrows on both ends' },
  { name: 'arrow_inward', title: 'Arrows pointing inward' }
]
