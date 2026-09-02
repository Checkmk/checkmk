/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref, watch } from 'vue'

import type { SummaryChip } from '@/maps/map/detail/composables/useSummaryChips'
import { useMapsApis } from '@/maps/services/context'
import type { AggregationNode, BulkAckTarget, MapElement, ObjectState } from '@/maps/types/api'
import {
  BI_STATE_FULL_LABEL,
  BI_STATE_LABEL as BI_STATE_LABEL_MAP,
  BI_STATE_TONE,
  walkAggregationLeavesWithPath
} from '@/maps/utils/aggregationTree'
import { buildCheckmkSetupUrl } from '@/maps/utils/mapNavigation'
import { newObjectState } from '@/maps/utils/model'

export interface AggregationLeafRow {
  id: string
  label: string
  stateLabel: string
  tone: 'ok' | 'warn' | 'crit' | 'unknown'
  /** Walked path back to root, used for "worstPath" display. */
  path: string[]
  hostName: string | null
  serviceDescription: string | null
  state: number
  output: string
}

export interface AggregationSummary {
  chips: SummaryChip[]
  worstPath: string | null
  worstOutput: string | null
  leaves: AggregationLeafRow[]
  /** Nodes at depth=`expand_depth` (or shallower terminal bi_leaves). */
  treeRows: AggregationLeafRow[]
  treeChips: SummaryChip[]
  treeDepth: number
}

type AggregationView = 'summary' | 'details'

// Operator-facing labels for the BI severity ordering: CRIT > WARN > UNKN > OK.
// Used for chip layout, "worst leaf" sort, and tree-node count breakdown.
const BI_CHIP_ORDER: readonly number[] = [2, 1, 3, 0]

function _aggregationRow(node: AggregationNode, path: string[]): AggregationLeafRow {
  const fullPath = [...path, node.name]
  return {
    id: fullPath.join('::'),
    label: node.name,
    stateLabel: BI_STATE_LABEL_MAP[node.state] ?? String(node.state),
    tone: BI_STATE_TONE[node.state] ?? 'unknown',
    path: fullPath,
    hostName: node.host_name ?? null,
    serviceDescription: node.service_description ?? null,
    state: node.state,
    output: node.output ?? ''
  }
}

function _walkAggregationLeaves(node: AggregationNode): AggregationLeafRow[] {
  return walkAggregationLeavesWithPath(node).map(({ leaf, path }) =>
    _aggregationRow(leaf, path.slice(0, -1))
  )
}

// Collect nodes at exactly `targetDepth` below root. A branch shorter than
// targetDepth terminates at its real bi_leaf — no synthetic placeholders.
// Root itself is never returned (caller starts with empty path).
function _nodesAtDepth(
  node: AggregationNode,
  targetDepth: number,
  path: string[] = []
): AggregationLeafRow[] {
  if (targetDepth === 0) {
    return path.length > 0 ? [_aggregationRow(node, path)] : []
  }
  if (node.children.length === 0) {
    return path.length > 0 ? [_aggregationRow(node, path)] : []
  }
  const next = [...path, node.name]
  return node.children.flatMap((c) => _nodesAtDepth(c, targetDepth - 1, next))
}

function _chipsFromCounts(counts: Record<number, number>): SummaryChip[] {
  return BI_CHIP_ORDER.map((s) => ({
    state: BI_STATE_LABEL_MAP[s] ?? String(s),
    count: counts[s] ?? 0,
    label: BI_STATE_LABEL_MAP[s] ?? String(s),
    tone: BI_STATE_TONE[s] ?? 'unknown',
    url: null
  }))
}

function _countByState(rows: ReadonlyArray<{ state: number }>): Record<number, number> {
  const out: Record<number, number> = { 0: 0, 1: 0, 2: 0, 3: 0 }
  for (const r of rows) {
    out[r.state] = (out[r.state] ?? 0) + 1
  }
  return out
}

interface AggregationDetailOptions {
  object: () => MapElement | null
  state: () => ObjectState | undefined
  checkmkUrl: () => string | null | undefined
  connectionId: () => string | null | undefined
  onSelectHost: (
    host: string,
    service: string | null,
    seed: Omit<ObjectState, 'object_id'> | null
  ) => void
  onBulkAcknowledge: (targets: BulkAckTarget[]) => void
}

/**
 * BI aggregation section of the drawer: pack-id lookup for the Setup deep-link,
 * the summary/details view toggle, leaf/tree chip rows, drilldown into a leaf
 * (seeded so a stateless BI leaf still renders status), and bulk-acknowledge of
 * the contributing problem leaves. The two outbound actions (drilldown, bulk
 * ack) are injected as callbacks.
 */
export function useAggregationDetail(options: AggregationDetailOptions) {
  const { object, state, checkmkUrl, connectionId, onSelectHost, onBulkAcknowledge } = options
  const { objects } = useMapsApis()
  const { _t } = usei18n()

  // Map values: string = pack id; null = looked up but not surfaced by cmk.bi
  // (cache the negative so subsequent drawer opens don't re-fetch the catalog).
  const aggregationPackIds = ref<Record<string, string | null>>({})
  watch(
    () => [object()?.type, object()?.aggregation_id, connectionId()] as const,
    async ([type, aggId, connId]) => {
      if (type !== 'aggregation' || !aggId || !connId) {
        return
      }
      if (aggId in aggregationPackIds.value) {
        return
      }
      try {
        const aggrs = await objects.fetchAggregations()
        const next: Record<string, string | null> = { ...aggregationPackIds.value }
        for (const a of aggrs) {
          next[a.id] = a.pack_id || null
        }
        if (!(aggId in next)) {
          next[aggId] = null
        }
        aggregationPackIds.value = next
      } catch {
        // Pack-id lookup failure means we fall back to the bi_packs overview
        // link, which is fine; nothing to do here.
      }
    },
    { immediate: true }
  )

  const checkmkSetupUrlFull = computed(() => {
    const obj = object()
    if (!obj) {
      return null
    }
    const aggId = obj.aggregation_id ?? null
    const packId = aggId ? aggregationPackIds.value[aggId] : null
    return buildCheckmkSetupUrl(obj, checkmkUrl() ?? null, packId ?? null, state()?.site_id)
  })

  const aggregationSummary = computed<AggregationSummary | null>(() => {
    const obj = object()
    const tree = state()?.tree
    if (!obj || obj.type !== 'aggregation' || !tree) {
      return null
    }

    const leaves = _walkAggregationLeaves(tree)
    if (!leaves.length) {
      return null
    }

    const chips = _chipsFromCounts(_countByState(leaves))

    // Worst-leaf sort follows BI_CHIP_ORDER so ties resolve deterministically
    // to the highest-severity slot (CRIT > WARN > UNKN > OK).
    const sorted = [...leaves].sort(
      (a, b) => BI_CHIP_ORDER.indexOf(a.state) - BI_CHIP_ORDER.indexOf(b.state)
    )
    const worst = sorted.find((l) => l.state > 0) ?? null
    const worstPath = worst ? worst.path.join(' › ') : null
    const worstOutput = worst?.output || null

    const expandDepth = obj.expand_depth ?? 0
    if (expandDepth === 0) {
      return {
        chips,
        worstPath,
        worstOutput,
        leaves: sorted,
        treeRows: [],
        treeChips: [],
        treeDepth: 0
      }
    }

    const treeRows = _nodesAtDepth(tree, expandDepth)
    const treeChips = _chipsFromCounts(_countByState(treeRows))

    return {
      chips,
      worstPath,
      worstOutput,
      leaves: sorted,
      treeRows,
      treeChips,
      treeDepth: expandDepth
    }
  })

  const aggregationView = ref<AggregationView>('summary')
  // Re-pick the default view only when the operator switches to a different
  // object — otherwise an edit to expand_depth would clobber a manual tab
  // choice in the open drawer.
  watch(
    () => object()?.id,
    () => {
      aggregationView.value = (object()?.expand_depth ?? 0) > 0 ? 'summary' : 'details'
    },
    { immediate: true }
  )

  const aggregationViewOptions = computed(() => {
    const d = aggregationSummary.value?.treeDepth ?? 1
    return [
      {
        label: _t('Summary (depth %{depth})', { depth: d }),
        value: 'summary'
      },
      { label: _t('Details'), value: 'details' }
    ]
  })

  function setAggregationView(v: string): void {
    if (v === 'summary' || v === 'details') {
      aggregationView.value = v
    }
  }

  const aggregationListRows = computed<AggregationLeafRow[]>(() => {
    const s = aggregationSummary.value
    if (!s) {
      return []
    }
    return aggregationView.value === 'summary' ? s.treeRows : s.leaves
  })

  // Service leaves repeat generic names ("PING") across hosts in multi-host
  // aggregations — prefix the host so rows stay unambiguous. Single-host
  // trees skip the prefix (pure noise there).
  const aggregationListMultiHost = computed(() => {
    const hosts = new Set(
      aggregationListRows.value.map((r) => r.hostName).filter((h): h is string => !!h)
    )
    return hosts.size > 1
  })

  const activeChips = computed<SummaryChip[]>(() => {
    const s = aggregationSummary.value
    if (!s) {
      return []
    }
    return aggregationView.value === 'summary' ? s.treeChips : s.chips
  })

  function onAggregationLeafClick(leaf: AggregationLeafRow): void {
    if (!leaf.hostName) {
      return
    }
    // Seed a node-derived state: BI leaves usually have no map-state entry,
    // so without it the drilled-into drawer would render statusless (actions
    // only). BI encodes host leaves in service codes too — map 0 to UP and
    // anything worse to DOWN for the host pill.
    const isService = !!leaf.serviceDescription
    const seed: Omit<ObjectState, 'object_id'> = newObjectState({
      object_id: '',
      type: isService ? 'service' : 'host',
      state: isService
        ? (BI_STATE_FULL_LABEL[leaf.state] ?? 'PENDING')
        : leaf.state === 0
          ? 'UP'
          : 'DOWN',
      output: leaf.output
    })
    onSelectHost(leaf.hostName, leaf.serviceDescription ?? null, seed)
  }

  const aggregationProblemLeaves = computed<AggregationLeafRow[]>(() => {
    const summary = aggregationSummary.value
    if (!summary) {
      return []
    }
    // state>0 = WARN/CRIT/UNKN; OK leaves don't need ack.
    return summary.leaves.filter((l) => l.state > 0 && !!l.hostName)
  })

  function onBulkAcknowledgeClick(): void {
    if (!aggregationProblemLeaves.value.length) {
      return
    }
    onBulkAcknowledge(
      aggregationProblemLeaves.value.map((l) => ({
        host: l.hostName as string,
        service: l.serviceDescription ?? null
      }))
    )
  }

  return {
    checkmkSetupUrlFull,
    aggregationSummary,
    aggregationView,
    aggregationViewOptions,
    setAggregationView,
    aggregationListRows,
    aggregationListMultiHost,
    activeChips,
    onAggregationLeafClick,
    aggregationProblemLeaves,
    onBulkAcknowledgeClick
  }
}
