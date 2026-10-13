/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { AggregationNode } from '@/maps/types/api'
import {
  BI_STATE_FULL_LABEL,
  BI_STATE_LABEL,
  aggregationLeafId,
  countLeavesByState,
  flattenAggregationLeaves
} from '@/maps/utils/aggregationTree'
import type { TranslateFn } from '@/maps/utils/dropdownOptions'
import { stateColorVar } from '@/maps/utils/stateColors'

/** How many leaves the preview names before it only counts the rest. */
const SAMPLE_SIZE = 5

/**
 * Above this many leaves an expanded aggregation crowds the map: dozens of
 * state circles around the root glyph. The number is empirical — most
 * multi-host aggregations fan out to 20-40 leaves, so 50 is where it starts to
 * look like a mistake.
 */
const CROWDED_LEAF_COUNT = 50

/** The four BI states in the order the preview lists them: problems first. */
const STATE_ORDER = [2, 1, 3, 0]

export interface StateCount {
  key: string
  label: string
  color: string
  count: number
}

export interface LeafSample {
  id: string
  label: string
  color: string
}

/** One entry per BI state with how many leaves are in it. */
export function leafStateCounts(leaves: AggregationNode[]): StateCount[] {
  const counts = countLeavesByState(leaves)
  return STATE_ORDER.map((state) => ({
    key: String(state),
    label: BI_STATE_LABEL[state] ?? '',
    color: stateColorVar(BI_STATE_FULL_LABEL[state]),
    count: counts[state] ?? 0
  }))
}

/** The first few leaves, each with the colour of its state. */
export function leafSample(leaves: AggregationNode[]): LeafSample[] {
  return leaves.slice(0, SAMPLE_SIZE).map((leaf) => ({
    id: aggregationLeafId(leaf),
    label: leaf.name,
    color: stateColorVar(BI_STATE_FULL_LABEL[leaf.state] ?? 'UNKNOWN')
  }))
}

/** How many leaves the sample above left out. */
export function leavesBeyondSample(leaves: AggregationNode[]): number {
  return Math.max(0, leaves.length - SAMPLE_SIZE)
}

export function leavesOf(tree: AggregationNode | null): AggregationNode[] {
  return tree ? flattenAggregationLeaves(tree) : []
}

/**
 * Warns when the picked depth would draw more leaves than a map can carry, and
 * says what to do instead. Null while the fan-out is still comfortable, and for
 * depth 0 — that draws the root glyph alone no matter how big the tree is.
 */
export function crowdingWarning(
  leaves: AggregationNode[],
  expandDepth: number,
  _t: TranslateFn
): TranslatedString | null {
  if (expandDepth <= 0 || leaves.length <= CROWDED_LEAF_COUNT) {
    return null
  }
  return _t(
    '%{count} nodes — the subtree will be very crowded on the map. Set expand depth to 0 to keep only the root glyph and drill into details via the drawer.',
    { count: leaves.length }
  )
}
