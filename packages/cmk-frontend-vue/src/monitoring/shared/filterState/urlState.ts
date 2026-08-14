/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { computed } from 'vue'

import type { MonitoringService } from '@/monitoring/shared/services/MonitoringService'
import { readUrlState } from '@/monitoring/shared/urlState/readUrlState'
import type { UrlStateFormat, UrlStateWriter } from '@/monitoring/shared/urlState/types'

import { FILTER_STATE_KEYS, flatFilterUrlCodec } from './codec'
import { reconcile } from './reconcile'
import type { FilterUrlSchema, FilterUrlState, RawFilterUrlState } from './types'

const NAME = 'filter state'

/** How a table's row-narrowing state is spelled in the URL. */
export function filterStateFormat(
  schema: FilterUrlSchema
): UrlStateFormat<FilterUrlState, RawFilterUrlState> {
  return {
    name: NAME,
    keys: FILTER_STATE_KEYS,
    codec: flatFilterUrlCodec,
    reconcile: (raw) => reconcile(raw, schema)
  }
}

/** Decodes and reconciles the filter and applied-search state currently in the URL. */
export function readFilterUrlState(search: string, schema: FilterUrlSchema): FilterUrlState {
  return readUrlState(filterStateFormat(schema), search)
}

/**
 * The table's filter and applied-search state as a slice for `useUrlSync` to
 * mirror. Encoding needs no schema, unlike reading: what a field is called is
 * the API's vocabulary, and reconciliation on the way in has already dropped
 * whatever this table does not filter.
 */
export function filterStateWriter<T>(service: MonitoringService<T>): UrlStateWriter {
  return {
    name: NAME,
    keys: FILTER_STATE_KEYS,
    params: computed(() => flatFilterUrlCodec.encode(service.filterUrlState.value))
  }
}
