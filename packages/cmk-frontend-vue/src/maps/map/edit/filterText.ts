/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { TranslateFn } from '@/maps/utils/dropdownOptions'

// The lines the server takes (``normalize_object_filter``); it checks the rest.
const FILTER_LINE = /^(Filter|And|Or|Negate):/
// Where Python's ``splitlines()`` breaks a line, as the server does.
const LINE_BREAK = /\r\n|[\n\r\v\f\u0085\u2028\u2029]/

function filterLines(filter: string): string[] {
  return filter
    .replaceAll('\\n', '\n')
    .split(LINE_BREAK)
    .map((line) => line.trim())
    .filter((line) => line !== '')
}

/** Whether every line of a filter is one Livestatus takes, NagVis' ``\\n`` included. */
export function isFilterWellFormed(filter: string): boolean {
  return filterLines(filter).every((line) => FILTER_LINE.test(line))
}

/** Whether a filter has a line at all, which a dynamic group needs. */
export function hasFilterLines(filter: string): boolean {
  return filterLines(filter).length > 0
}

/** What to say at a filter the server would refuse for its lines. */
export function filterProblems(_t: TranslateFn, filter: string): TranslatedString[] {
  return isFilterWellFormed(filter)
    ? []
    : [
        _t('Start each line with %{headers}.', {
          headers: '"Filter:", "And:", "Or:" or "Negate:"'
        })
      ]
}
