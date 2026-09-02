/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * What a graph object on a static map plots.
 *
 * A graph object names a host or service and, optionally, a graph template or a
 * set of metrics. Turning that into series means asking the daemon for the
 * metric history and Checkmk's GUI for the display semantics (which metrics
 * belong to which graph, which half of a bidirectional graph a metric is on,
 * titles, units, colours), then windowing the samples to what the object asks
 * to show.
 */
import { type Ref, computed, onMounted, onUnmounted, ref, watch } from 'vue'

import { useMetricInfo } from '@/maps/map/composables/useMetricInfo'
import {
  metricColorsOf,
  metricTitlesOf,
  metricUnitsOf
} from '@/maps/map/composables/useMetricUnits'
import { useAuth, useStates } from '@/maps/services/context'
import type { MapElement, MetricPoint, MetricUnitMap, ObjectState } from '@/maps/types/api'
import { getMapElementIdentifier } from '@/maps/utils/naming'
import { getMetric, parsePerfData } from '@/maps/utils/perf'

/** How long to wait for the first sample before saying there is none. */
const DATA_TIMEOUT_MS = 15_000

const DEFAULT_WINDOW_MINUTES = 60

/** One drawn graph: a template group, or everything the object asked for. */
export interface ChartGroup {
  id: string
  title: string
  data: Record<string, MetricPoint[]>
  /** Labels drawn below the axis (a bidirectional graph's lower half). */
  mirrored: string[]
}

export interface MapElementChartModel {
  /** Whether any series has a sample yet. */
  hasData: Ref<boolean>
  /** Whether the wait for a first sample has been given up on. */
  timedOut: Ref<boolean>
  groups: Ref<ChartGroup[]>
  /** Raw perfdata labels drawn, in drawing order. */
  keys: Ref<string[]>
  /** Display label per drawn series, in the same order as ``keys``. */
  labels: Ref<string[]>
  /** What the card is titled when it draws more than one series. */
  headerName: Ref<string>
  units: Ref<MetricUnitMap>
  colors: Ref<Record<string, string>>
  titles: Ref<Record<string, string>>
  /** Warn/crit levels of the object's leading metric. */
  thresholds: Ref<{ warn: number | null; crit: number | null } | null>
  windowSecs: Ref<number>
  /** Latest reading of one series, formatted as Checkmk formats it. */
  latest: (key: string) => MetricPoint | undefined
}

export function useMapElementChart(source: {
  object: () => MapElement
  state: () => ObjectState | undefined
  connectionId: () => string | undefined
  enabled: () => boolean
}): MapElementChartModel {
  const states = useStates()
  const auth = useAuth()

  const windowMinutes = computed(() => source.object().graph_time_window ?? DEFAULT_WINDOW_MINUTES)
  const windowSecs = computed(() => windowMinutes.value * 60)

  // Graph objects additionally need the graph groups (which metrics belong
  // together, and which of them are mirrored), so the lookup is the opt-in one.
  const { info } = useMetricInfo({
    connectionId: source.connectionId,
    hostName: () => source.object().host_name,
    serviceDescription: () => source.object().service_description,
    perfData: () => source.state()?.perf_data,
    checkCommand: () => source.state()?.check_command,
    siteId: () => source.state()?.site_id,
    graphs: () => true,
    enabled: source.enabled
  })

  const units = computed(() => metricUnitsOf(info.value))
  const colors = computed(() => metricColorsOf(info.value))
  // Registry titles win; the titles a backend supplies itself (the remote REST
  // metric endpoint, the demo connection) fill the gaps.
  const titles = computed(() => ({
    ...(states.metricTitles.value[source.object().id] ?? {}),
    ...metricTitlesOf(info.value)
  }))
  const graphGroups = computed(() => info.value?.graphs ?? [])

  const data = computed((): Record<string, MetricPoint[]> => {
    const object = source.object()
    const series = source.enabled() ? states.metricValues.value[object.id] : undefined
    if (!series) {
      return {}
    }
    const cutoff = Date.now() / 1000 - windowSecs.value

    const windowed = (points: MetricPoint[]): MetricPoint[] => {
      const inWindow = points.filter((point) => point.ts >= cutoff)
      if (inWindow.length) {
        return inWindow
      }
      // Nothing in the window yet: show the last reading as a baseline rather
      // than an empty graph.
      const last = points.at(-1)
      return last ? [last] : []
    }
    const pick = (keys: string[]): Record<string, MetricPoint[]> =>
      Object.fromEntries(
        keys.filter((key) => series[key]).map((key) => [key, windowed(series[key]!)])
      )

    if (object.graph_metric?.length) {
      return pick(object.graph_metric)
    }
    const pinned = object.graph_id
      ? graphGroups.value.find((group) => group.id === object.graph_id)
      : undefined
    if (pinned) {
      return pick(pinned.metrics)
    }
    return Object.fromEntries(
      Object.entries(series).map(([key, points]) => [key, windowed(points)])
    )
  })

  const groups = computed((): ChartGroup[] => {
    const object = source.object()
    const available = graphGroups.value
    // ``graph_metric`` and ``graph_id`` already narrowed ``data``, so an
    // explicit pick draws as one ungrouped graph.
    if (!available.length || object.graph_id || object.graph_metric?.length) {
      const pinned = object.graph_id
        ? available.find((group) => group.id === object.graph_id)
        : undefined
      return [{ id: '_all', title: '', data: data.value, mirrored: pinned?.mirrored ?? [] }]
    }
    // Several template groups apply but none was pinned: draw the first one
    // that has data. Drawing them all squeezes each into unreadability — the
    // operator picks one via ``graph_id``.
    for (const group of available) {
      const groupData = Object.fromEntries(
        group.metrics
          .filter((metric) => data.value[metric])
          .map((metric) => [metric, data.value[metric]!])
      )
      if (Object.keys(groupData).length > 0) {
        return [
          { id: group.id, title: group.title, data: groupData, mirrored: group.mirrored ?? [] }
        ]
      }
    }
    return [{ id: '_all', title: '', data: data.value, mirrored: [] }]
  })

  const keys = computed(() => Object.keys(data.value))
  const labels = computed(() => keys.value.map((key) => titles.value[key] ?? key))
  const hasData = computed(() => Object.values(data.value).some((points) => points.length > 0))

  const timedOut = ref(false)
  let timeoutTimer: ReturnType<typeof setTimeout> | null = null

  function requestHistory(): void {
    const object = source.object()
    const connectionId = source.connectionId()
    if (!source.enabled() || !object.host_name || !connectionId) {
      return
    }
    timedOut.value = false
    if (timeoutTimer) {
      clearTimeout(timeoutTimer)
    }
    timeoutTimer = setTimeout(() => {
      if (!hasData.value) {
        timedOut.value = true
      }
    }, DATA_TIMEOUT_MS)
    void states.prefillMetricHistory(
      object.id,
      connectionId,
      object.host_name,
      object.service_description ?? null,
      windowMinutes.value
    )
  }

  onMounted(requestHistory)
  watch(windowMinutes, requestHistory)
  // A rebound object's samples belong to the previous host or service.
  watch(
    () => [source.object().host_name, source.object().service_description],
    () => {
      states.clearMetricValues(source.object().id)
      requestHistory()
    }
  )
  // The request needs a session; retry once the handshake has resolved one.
  watch(
    () => auth.user.value,
    (user, previous) => {
      if (user && !previous) {
        requestHistory()
      }
    }
  )
  onUnmounted(() => {
    if (timeoutTimer) {
      clearTimeout(timeoutTimer)
    }
  })

  const headerName = computed(() => {
    // The graph template's title ("RAM (Total, cached, buffers)") says more
    // than the host name does, and is how Checkmk labels its own graphs.
    const only = groups.value.length === 1 ? groups.value[0] : undefined
    return only?.title || (getMapElementIdentifier(source.object()) ?? '')
  })

  const thresholds = computed(() => {
    if (!source.enabled()) {
      return null
    }
    const metric = getMetric(
      parsePerfData(source.state()?.perf_data ?? ''),
      source.object().graph_metric?.[0]
    )
    return metric ? { warn: metric.warn, crit: metric.crit } : null
  })

  return {
    hasData,
    timedOut,
    groups,
    keys,
    labels,
    headerName,
    units,
    colors,
    titles,
    thresholds,
    windowSecs,
    latest: (key) => data.value[key]?.at(-1)
  }
}
