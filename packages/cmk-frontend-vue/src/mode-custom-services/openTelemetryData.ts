/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref, watch } from 'vue'

import { fetchOpenTelemetryData } from './api'
import type { HostOpenTelemetryData } from './definition'

export type OpenTelemetryData =
  | { status: 'idle' }
  | { status: 'loaded'; hosts: HostOpenTelemetryData[] }
  | { status: 'failed' }

/** Whether saving enables "OpenTelemetry data" on the hosts, looked up whenever they change. */
export function useOpenTelemetryData(getHostNames: () => string[]): Ref<OpenTelemetryData> {
  const data = ref<OpenTelemetryData>({ status: 'idle' })
  let request = 0

  watch(
    () => getHostNames().join('\n'),
    async () => {
      const current = ++request
      const hostNames = getHostNames()
      data.value = { status: 'idle' }
      if (hostNames.length === 0) {
        return
      }
      try {
        const hosts = await fetchOpenTelemetryData(hostNames)
        if (current === request) {
          data.value = { status: 'loaded', hosts }
        }
      } catch {
        if (current === request) {
          data.value = { status: 'failed' }
        }
      }
    },
    { immediate: true }
  )

  return data
}
