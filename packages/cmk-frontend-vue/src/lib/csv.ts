/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

/** Prepended to a CSV file, it is what makes Excel read the file as UTF-8. */
export const CSV_BOM = '\uFEFF'

// A leading one of these makes a spreadsheet treat the cell as a formula. Exported
// values are data, never formulas, so any such cell is neutralized with a leading
// apostrophe.
const FORMULA_PREFIXES = ['=', '+', '-', '@', '\t', '\r']

/** `value` as one quoted CSV field, safe to open in a spreadsheet. */
export function csvField(value: string): string {
  const guarded = FORMULA_PREFIXES.some((prefix) => value.startsWith(prefix)) ? `'${value}` : value
  // Quote unconditionally: it is always valid, and it avoids having to decide
  // per value whether a separator, quote or newline is in there.
  return `"${guarded.replaceAll('"', '""')}"`
}
