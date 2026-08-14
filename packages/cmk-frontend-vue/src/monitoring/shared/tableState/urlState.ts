/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { computed } from 'vue'

import type { MonitoringService } from '@/monitoring/shared/services/MonitoringService'
import { readUrlState } from '@/monitoring/shared/urlState/readUrlState'
import type { UrlStateFormat, UrlStateWriter } from '@/monitoring/shared/urlState/types'

import { TABLE_STATE_KEYS, flatTableStateCodec } from './codec'
import { reconcile } from './reconcile'
import type { RawTableState, TableState, TableStateSchema } from './types'

const NAME = 'table state'

/**
 * How a table's non-filter display state is spelled in the URL. The schema is
 * bound here because encoding needs it to tell a chosen value from a default.
 */
export function tableStateFormat(
  schema: TableStateSchema
): UrlStateFormat<TableState, RawTableState> {
  return {
    name: NAME,
    keys: TABLE_STATE_KEYS,
    codec: {
      encode: (state) => flatTableStateCodec.encode(state, schema),
      decode: (params) => flatTableStateCodec.decode(params)
    },
    reconcile: (raw) => reconcile(raw, schema)
  }
}

/** Decodes and reconciles the display state currently in the URL. */
export function readTableStateFromUrl(search: string, schema: TableStateSchema): TableState {
  return readUrlState(tableStateFormat(schema), search)
}

/**
 * The table's display state as a slice for `useUrlSync` to mirror. Filters are
 * a separate slice: they narrow the result set and display state deliberately
 * never does.
 */
export function tableStateWriter<T>(
  service: MonitoringService<T>,
  schema: TableStateSchema
): UrlStateWriter {
  const format = tableStateFormat(schema)
  return {
    name: format.name,
    keys: format.keys,
    params: computed(() => format.codec.encode(service.tableState.value))
  }
}
