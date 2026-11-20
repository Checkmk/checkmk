/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { computed } from 'vue'

import type { UrlStateWriter } from '@/monitoring/shared/urlState/types'

/** The param a link from a legacy view names the filters in that it could not take over. */
const UNAPPLIED_FILTERS_KEY = 'unapplied'

/**
 * Drops the filters a link from a legacy view could not take over from the URL as soon as the
 * page is loaded. The page names them once, from its props: a reload or a shared link must not
 * name them again once the filters have changed.
 */
export function unappliedFiltersWriter(): UrlStateWriter {
  return {
    name: 'unapplied filters',
    keys: [UNAPPLIED_FILTERS_KEY],
    params: computed(() => ({ [UNAPPLIED_FILTERS_KEY]: null }))
  }
}
