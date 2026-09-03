/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed, ref, watch } from 'vue'

import { useMetricCatalog } from '@/maps/map/composables/useMetricInfo'
import { useStates } from '@/maps/services/context'
import { type SuggestionList, suggestionList, titledSuggestions } from '@/maps/shared/suggestions'
import type { MapElement, MetricChoice, MetricGraphGroup, ObjectState } from '@/maps/types/api'
import { parsePerfData } from '@/maps/utils/perf'

export interface ObjectMetrics {
  /** The object's metrics, by id, titled the way Checkmk titles them. */
  metrics: SuggestionList
  /** The graphs Checkmk would draw for the bound object. */
  graphTemplates: Readonly<Ref<MetricGraphGroup[]>>
  /** A metric id's human title, falling back to the id itself. */
  titleOf: (metricId: string) => string
}

interface ObjectMetricsOptions {
  object: () => MapElement
  state: () => ObjectState | undefined
  connectionId: () => string
  hostName: () => string
  serviceDescription: () => string
}

/**
 * What the object being edited measures: its metrics for the pickers, and the
 * graph templates Checkmk offers for it.
 *
 * The metric fetch carries Checkmk's own titles. Until it answers — and for
 * ids it does not cover — the perfdata of the live state stands in, so a
 * picker is never empty just because a request is still out.
 */
export function useObjectMetrics(options: ObjectMetricsOptions): ObjectMetrics {
  const { object, state, connectionId, hostName, serviceDescription } = options
  const { fetchMetricChoices, fetchGraphTemplates } = useMetricCatalog()
  const statesStore = useStates()

  const fetched = ref<MetricChoice[]>([])
  const graphTemplates = ref<MetricGraphGroup[]>([])

  const metricIds = computed<string[]>(() =>
    fetched.value.length
      ? fetched.value.map((metric) => metric.name)
      : parsePerfData(state()?.perf_data ?? '').map((metric) => metric.label)
  )

  const titles = computed<Record<string, string>>(() => ({
    ...(statesStore.metricTitles.value[object().id] ?? {}),
    ...Object.fromEntries(fetched.value.map((metric) => [metric.name, metric.title]))
  }))

  function titleOf(metricId: string): string {
    return titles.value[metricId] ?? metricId
  }

  const metrics = suggestionList(() =>
    titledSuggestions(metricIds.value.map((id) => ({ id, title: titleOf(id) })))
  )

  function report(what: string): (error: unknown) => never[] {
    return (error) => {
      console.warn(`[Maps] Failed to load ${what}:`, error)
      return []
    }
  }

  // The bound host and service change faster than the lookups answer, so only
  // the newest one may write — and clearing counts as a lookup too, or the
  // answer for the host just dropped would land on the empty field.
  let lookup = 0

  watch(
    () => [connectionId(), hostName(), serviceDescription()] as const,
    async ([connection, host, service]) => {
      const current = ++lookup
      if (!connection || !host) {
        fetched.value = []
        graphTemplates.value = []
        return
      }
      const choices = await fetchMetricChoices(host, service || null).catch(report('metrics'))
      const templates =
        object().type === 'graph'
          ? await fetchGraphTemplates(host, service || null, state()?.site_id ?? null).catch(
              report('graph templates')
            )
          : []
      if (current === lookup) {
        fetched.value = choices
        graphTemplates.value = templates
      }
    },
    { immediate: true }
  )

  return { metrics, graphTemplates, titleOf }
}
