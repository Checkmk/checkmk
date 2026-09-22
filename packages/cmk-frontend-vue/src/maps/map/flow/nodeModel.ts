/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * How the rest of the map reads a flow map's nodes.
 *
 * A flow node is not a map object: nobody placed it, and monitoring has no
 * entry for it under the id the map gave it. So everything the shared surfaces
 * need — the ``MapElement`` a hover card, a slide-in or a command is about, and
 * the ``ObjectState`` they show — is derived here from the topology the node
 * came from. A site root has no monitoring entry at all and is aggregated from
 * its member hosts on the fly.
 *
 * A plain factory rather than a composable: it holds no state and touches
 * nothing reactive, it only reads the getters it is given.
 */
import type usei18n from 'cmk-ui-library/lib/i18n'

import { type DonutSegment, HEALTHY_HOST_STATES } from '@/maps/map/flow/geometry'
import { serviceNameOf } from '@/maps/map/flow/nodeIds'
import type { CmdMarker, FNode } from '@/maps/map/flow/nodes'
import type { MapElement, ObjectState, TopologyNode } from '@/maps/types/api'
import { newObjectState } from '@/maps/utils/model'
import { stateColorVar } from '@/maps/utils/stateColors'

/**
 * The ``_t`` a component hands to a helper. Gettext extraction only sees literal
 * ``_t('…')`` call sites, so a helper takes the translator rather than
 * translating a dynamic key itself.
 */
type TranslateFn = ReturnType<typeof usei18n>['_t']

/** A hairline that just separates the node from the map, in any theme. */
const HALO_DEFAULT_STROKE = 'rgb(0 0 0 / 40%)'

interface FlowNodeModelOptions {
  nodes: () => TopologyNode[]
  connectionId: () => string | null | undefined
  /** The worst-affected hosts, which are drawn with a wider halo. */
  worstHostIds: () => Set<string>
}

export function createFlowNodeModel(options: FlowNodeModelOptions) {
  const { nodes, connectionId, worstHostIds } = options

  function worstServiceState(d: FNode): string | null {
    const s = d.topo?.services_summary
    if (!s) {
      return null
    }
    if (s.critical > 0) {
      return 'CRITICAL'
    }
    if (s.warning > 0) {
      return 'WARNING'
    }
    if (s.unknown > 0) {
      return 'UNKNOWN'
    }
    return null
  }

  function hostHalo(d: FNode): { stroke: string; width: number } {
    const isTopK = worstHostIds().has(d.id)
    if (!HEALTHY_HOST_STATES.has(d.state)) {
      return isTopK
        ? { stroke: stateColorVar(d.state), width: 4 }
        : { stroke: HALO_DEFAULT_STROKE, width: 1.5 }
    }
    const worst = worstServiceState(d)
    if (!worst) {
      return { stroke: HALO_DEFAULT_STROKE, width: 1.5 }
    }
    return { stroke: stateColorVar(worst), width: isTopK ? 4 : 2.5 }
  }

  // Command-state markers shown on a node, mirroring the static map's badges:
  // acknowledged / in downtime / notifications-disabled. Source is the host
  // (d.topo) or the service (d.svc); both carry the same flags. `_t` is injected
  // from the component so gettext extraction sees the literal callsites here.
  function commandMarkers(_t: TranslateFn, d: FNode): CmdMarker[] {
    const src = d.nodeType === 'service' ? d.svc : d.topo
    if (!src) {
      return []
    }
    const out: CmdMarker[] = []
    if (src.acknowledged) {
      out.push({
        key: 'ack',
        glyph: '✓',
        fill: 'var(--color-warning)',
        fg: '#18181b',
        title: _t('Acknowledged'),
        corner: 'tr'
      })
    }
    if (src.in_downtime) {
      out.push({
        key: 'dt',
        glyph: '‖',
        fill: 'var(--color-light-blue-50)',
        fg: '#ffffff',
        title: _t('In downtime'),
        corner: 'tl'
      })
    }
    if (src.notifications_enabled === false) {
      out.push({
        key: 'notif',
        glyph: '∅',
        fill: 'var(--font-color-dimmed)',
        fg: '#ffffff',
        title: _t('Notifications disabled'),
        corner: 'br'
      })
    }
    return out
  }

  function donutSegments(n: TopologyNode): DonutSegment[] {
    const s = n.services_summary
    if (!s) {
      return []
    }
    // Order matters visually: critical first so it dominates the top of the ring.
    const all: DonutSegment[] = [
      { state: 'CRITICAL', value: s.critical },
      { state: 'WARNING', value: s.warning },
      { state: 'UNKNOWN', value: s.unknown },
      { state: 'PENDING', value: s.pending },
      { state: 'OK', value: s.ok }
    ]
    return all.filter((seg) => seg.value > 0)
  }

  function mapElementFromFNode(d: FNode): MapElement {
    if (d.nodeType === 'site') {
      return {
        id: d.id,
        type: 'site',
        x: 0,
        y: 0,
        host_name: d.siteId ?? null
      } as MapElement
    }
    const isService = d.nodeType === 'service'
    const svcName = isService ? serviceNameOf(d.id) : undefined
    // "+N more" pseudo nodes resolve to their host so clicking opens the
    // host's full service list in Checkmk.
    const hostNameForCheckmk = isService || d.nodeType === 'more' ? d.hostId : d.id
    return {
      id: d.id,
      type: isService ? 'service' : 'host',
      x: 0,
      y: 0,
      host_name: hostNameForCheckmk,
      service_description: svcName,
      // The flow map has no state-map entry to read site_id from, so carry
      // it from the topology node — commands need it to hit the right site.
      // Services and "+N more" nodes carry the host via parentTopo; host nodes
      // via topo.
      site_id: (isService || d.nodeType === 'more' ? d.parentTopo : d.topo)?.site_id ?? null
    } as MapElement
  }

  function siteHostsAggregate(siteId: string): {
    hostCount: number
    hostsUp: number
    hostsDown: number
    hostsUnreachable: number
    summary: { ok: number; warning: number; critical: number; unknown: number; pending: number }
  } {
    let hostCount = 0
    let hostsUp = 0
    let hostsDown = 0
    let hostsUnreachable = 0
    const summary = { ok: 0, warning: 0, critical: 0, unknown: 0, pending: 0 }
    for (const n of nodes()) {
      const sid = n.site_id || connectionId()
      if (sid !== siteId) {
        continue
      }
      hostCount++
      if (n.state === 'UP') {
        hostsUp++
      } else if (n.state === 'DOWN') {
        hostsDown++
      } else if (n.state === 'UNREACHABLE') {
        hostsUnreachable++
      }
      const s = n.services_summary
      if (s) {
        summary.ok += s.ok
        summary.warning += s.warning
        summary.critical += s.critical
        summary.unknown += s.unknown
        summary.pending += s.pending
      }
    }
    return { hostCount, hostsUp, hostsDown, hostsUnreachable, summary }
  }

  function objectStateFromFNode(d: FNode): ObjectState {
    if (d.nodeType === 'site') {
      const agg = siteHostsAggregate(d.siteId ?? '')
      // Site state aggregation rules:
      // - DOWN: every host on this site is DOWN/UNREACHABLE (site itself is offline)
      // - CRITICAL: at least one host is DOWN/UNREACHABLE OR has critical services
      // - WARNING: at least one warning/unknown service, no criticals
      // - UP: everything is healthy
      // A single down host out of hundreds shouldn't paint the whole site
      // DOWN — that would mask the real picture during partial outages.
      const allDown = agg.hostCount > 0 && agg.hostsDown + agg.hostsUnreachable === agg.hostCount
      const anyDown = agg.hostsDown + agg.hostsUnreachable > 0
      const worst = allDown
        ? 'DOWN'
        : anyDown || agg.summary.critical > 0
          ? 'CRITICAL'
          : agg.summary.warning > 0 || agg.summary.unknown > 0
            ? 'WARNING'
            : 'UP'
      return newObjectState({
        object_id: d.id,
        type: 'site',
        state: worst,
        output:
          `${agg.hostCount} hosts ` +
          `(${agg.hostsUp} up, ${agg.hostsDown} down, ${agg.hostsUnreachable} unreachable)`,
        site_id: d.siteId ?? null,
        services_summary: agg.summary
      })
    }
    if (d.nodeType === 'service') {
      const svc = d.svc
      const parent = d.parentTopo
      return newObjectState({
        object_id: d.id,
        type: 'service',
        state: d.state,
        output: d.output,
        acknowledged: svc?.acknowledged ?? false,
        in_downtime: svc?.in_downtime ?? false,
        notifications_enabled: svc?.notifications_enabled ?? true,
        active_checks_enabled: parent?.active_checks_enabled ?? true,
        ...(parent?.alias !== undefined && { alias: parent.alias }),
        ...(parent?.address !== undefined && { address: parent.address }),
        site_id: parent?.site_id ?? null,
        last_check: svc?.last_check ?? null,
        next_check: svc?.next_check ?? null,
        last_state_change: svc?.last_state_change ?? null,
        services_summary: null
      })
    }
    const topo = d.topo
    return newObjectState({
      object_id: d.id,
      type: d.nodeType,
      state: d.state,
      output: d.output,
      acknowledged: topo?.acknowledged ?? false,
      in_downtime: topo?.in_downtime ?? false,
      notifications_enabled: topo?.notifications_enabled ?? true,
      active_checks_enabled: topo?.active_checks_enabled ?? true,
      ...(topo?.alias !== undefined && { alias: topo.alias }),
      ...(topo?.address !== undefined && { address: topo.address }),
      site_id: topo?.site_id ?? null,
      last_check: topo?.last_check ?? null,
      next_check: topo?.next_check ?? null,
      last_state_change: topo?.last_state_change ?? null,
      ...(topo?.state_type !== undefined && { state_type: topo.state_type }),
      ...(topo?.current_attempt !== undefined && { current_attempt: topo.current_attempt }),
      ...(topo?.max_attempts !== undefined && { max_attempts: topo.max_attempts }),
      services_summary: topo?.services_summary ?? null
    })
  }

  /**
   * A host's live state by name, for the places that have a hostname rather
   * than a node — the jump out of the slide-in's topology section. Read off the
   * current topology, so what it hands back is never a snapshot.
   */
  function hostStateByName(hostName: string): ObjectState | undefined {
    const topo = nodes().find((candidate) => candidate.name === hostName)
    if (!topo) {
      return undefined
    }
    return objectStateFromFNode({
      id: hostName,
      state: topo.state,
      output: topo.output,
      bfsLevel: 0,
      nodeType: 'host',
      topo
    })
  }

  return {
    worstServiceState,
    /** Whether this host is one of the worst-affected. */
    isWorst: (d: FNode): boolean => worstHostIds().has(d.id),
    hostHalo,
    commandMarkers,
    donutSegments,
    mapElementFromFNode,
    objectStateFromFNode,
    hostStateByName
  }
}
