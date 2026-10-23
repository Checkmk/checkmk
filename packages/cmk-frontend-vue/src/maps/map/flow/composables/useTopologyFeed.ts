/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import { onMounted, onUnmounted, readonly, ref, watch } from 'vue'

import { useMapsApis, useStates } from '@/maps/services/context'
import type { FlowView, TopologyNode } from '@/maps/types/api'

interface TopologyFeedOptions {
  /** Empty while the map has no connection configured. */
  connectionId: () => string
  flowView: () => FlowView | null | undefined
  /** Whether the current service layout needs per-service detail in the fetch. */
  withServices: () => boolean
}

/**
 * Topology data source for the flow map.
 *
 * Primary: the central state stream pushes `topology_update` deltas via
 * statesStore.topology (scoped per auth_user); we mirror them into `nodes`.
 *
 * Fallback: when the stream never opens (a reverse proxy that will not pass
 * `text/event-stream`), the states store reports it unavailable and this polls
 * `/topology` every 15 s, pausing while the tab is hidden. The poll timer +
 * bootstrap timer + visibilitychange listener are owned and cleaned up here;
 * the view and the canvas keep their own lifecycles.
 */
export function useTopologyFeed(options: TopologyFeedOptions) {
  const { connectionId, flowView, withServices } = options
  const { _t } = usei18n()
  const { connections: connectionsApi } = useMapsApis()
  const statesStore = useStates()

  const nodes = ref<TopologyNode[]>([])
  const loading = ref(true)
  const error = ref('')
  let timer: ReturnType<typeof setInterval> | null = null
  let bootstrapTimer: ReturnType<typeof setTimeout> | null = null
  // Monotonic token so a slower earlier fetch (bootstrap vs. an overlapping
  // poll) can't publish after a newer one.
  let fetchSeq = 0

  /**
   * Asks for the topology. ``reset`` says the previous answer no longer applies
   * — a different root, a different connection — so the map shows nothing
   * rather than the old hosts while the new answer is on its way.
   */
  async function fetchTopology({ reset = false }: { reset?: boolean } = {}) {
    // A flow map without a connection has nothing to ask; the view says so.
    if (!connectionId()) {
      loading.value = false
      return
    }
    if (reset) {
      loading.value = true
    }
    const seq = ++fetchSeq
    try {
      const view = flowView()
      const topo = await connectionsApi.fetchTopology(connectionId(), withServices(), {
        root: view?.root ?? null,
        childLayers: view?.child_layers ?? null,
        parentLayers: view?.parent_layers ?? null,
        topAffectedHosts: view?.top_affected_hosts ?? null,
        servicesPerHost: view?.max_services_per_host ?? null
      })
      if (seq !== fetchSeq) {
        return
      }
      // With a live stream this REST call is only a bootstrap fallback; if the
      // feed has since delivered topology, keep it rather than clobbering it
      // with this older snapshot.
      if (!(statesStore.streamAvailable.value && statesStore.topologyReady.value)) {
        nodes.value = topo
      }
      if (error.value) {
        error.value = ''
      }
    } catch (e) {
      if (seq === fetchSeq) {
        error.value = e instanceof Error ? e.message : _t('Failed to load topology')
      }
    } finally {
      if (seq === fetchSeq) {
        loading.value = false
      }
    }
  }

  watch(
    () => statesStore.topology.value,
    (topo) => {
      if (!statesStore.streamAvailable.value) {
        return
      }
      nodes.value = [...topo]
      if (error.value) {
        error.value = ''
      }
      loading.value = false
    },
    { deep: false }
  )

  // Polling-fallback timer (only used without a stream). Tab-visibility
  // pause keeps idle multi-tab setups from each driving their own round-trip.
  function startPollTimer(): void {
    if (timer || statesStore.streamAvailable.value) {
      return
    }
    timer = setInterval(() => void fetchTopology(), 15000)
  }
  function stopPollTimer(): void {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }
  function onVisibilityChange(): void {
    if (statesStore.streamAvailable.value) {
      return
    }
    if (document.hidden) {
      stopPollTimer()
    } else {
      void fetchTopology()
      startPollTimer()
    }
  }

  watch(
    () => statesStore.streamAvailable.value,
    (available) => {
      if (!available) {
        void fetchTopology()
        if (!document.hidden) {
          startPollTimer()
        }
      } else {
        stopPollTimer()
      }
    }
  )

  onMounted(() => {
    if (statesStore.topology.value.length > 0) {
      nodes.value = [...statesStore.topology.value]
      loading.value = false
    } else if (statesStore.streamAvailable.value) {
      // Wait briefly for the first streamed topology_update; if none arrives, fall
      // back to a one-shot REST fetch so the user isn't stuck on a blank map.
      bootstrapTimer = setTimeout(() => {
        if (!statesStore.topologyReady.value && nodes.value.length === 0) {
          void fetchTopology()
        }
      }, 2000)
    } else {
      void fetchTopology()
      if (!document.hidden) {
        startPollTimer()
      }
    }
    document.addEventListener('visibilitychange', onVisibilityChange)
  })

  onUnmounted(() => {
    document.removeEventListener('visibilitychange', onVisibilityChange)
    if (bootstrapTimer) {
      clearTimeout(bootstrapTimer)
    }
    stopPollTimer()
  })

  return { nodes, loading: readonly(loading), error, fetchTopology }
}
