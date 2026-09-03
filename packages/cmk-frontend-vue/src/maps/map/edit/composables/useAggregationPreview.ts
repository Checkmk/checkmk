/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref, watch } from 'vue'

import { useMapsApis } from '@/maps/services/context'
import type { AggregationNode } from '@/maps/types/api'

export interface AggregationPreview {
  tree: Readonly<Ref<AggregationNode | null>>
  /** False once a probe failed, which is why there is no tree. */
  connectionOk: Readonly<Ref<boolean>>
}

/**
 * The BI tree behind the aggregation an operator is about to place, at the
 * expand depth they picked — so the fan-out is visible before the object lands
 * on the map.
 *
 * Typing moves fast and the tree fetch does not: only the newest request may
 * write its result, otherwise a slower earlier answer flickers back in.
 */
export function useAggregationPreview(options: {
  connectionId: () => string
  aggregationId: () => string
  expandDepth: () => number
}): AggregationPreview {
  const { objects } = useMapsApis()

  const tree = ref<AggregationNode | null>(null)
  const connectionOk = ref(true)

  let request = 0

  async function refresh(): Promise<void> {
    const aggregationId = options.aggregationId()
    if (!options.connectionId() || !aggregationId) {
      tree.value = null
      connectionOk.value = true
      return
    }
    const mine = ++request
    // Depth 0 means "root glyph only" on the map, but a preview of nothing is
    // useless — one level always shows what the root stands for.
    const depth = Math.max(1, options.expandDepth())
    try {
      const result = await objects.fetchAggregationTree(aggregationId, depth)
      if (mine === request) {
        tree.value = result.tree
        connectionOk.value = result.connection_ok
      }
    } catch {
      if (mine === request) {
        tree.value = null
        connectionOk.value = false
      }
    }
  }

  watch(
    () => [options.connectionId(), options.aggregationId(), options.expandDepth()] as const,
    () => void refresh(),
    { immediate: true }
  )

  return { tree, connectionOk }
}
