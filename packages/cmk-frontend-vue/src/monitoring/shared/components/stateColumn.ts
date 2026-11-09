/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef } from '@tanstack/vue-table'
import { type ComputedRef, computed, ref, watch } from 'vue'

import type { MonitoringIcon } from '@/monitoring/shared/api/types'
import { columnId } from '@/monitoring/shared/tableState/schema'

import { CELL_PADDING } from './MonitoringTableContext'

export const STATE_COLUMN_ID = 'state'

/** The modes the State column shows after stale and flapping, in this order. */
const STATE_MODE_IDS = ['acknowledged', 'downtime', 'comments'] as const
const STATE_MODE_ID_SET: ReadonlySet<string> = new Set(STATE_MODE_IDS)

/** The most icons a state tag has beside it: stale, flapping and every state mode. */
const MAX_STATE_ICONS = 2 + STATE_MODE_IDS.length

/** The boolean fields the State column renders as icons and offers as filter flags. */
export type StateFlagField =
  | 'stale'
  | 'is_flapping'
  | 'acknowledged'
  | 'in_downtime'
  | 'has_comments'

type ModeLike = MonitoringIcon & { id: string }

export interface RowWithStateIcons {
  stale?: boolean | null | undefined
  is_flapping?: boolean | null | undefined
  modes?: readonly ModeLike[] | null | undefined
}

/** The modes of a row the State column shows, in their fixed order. */
export function stateModes<M extends ModeLike>(modes: readonly M[] | null | undefined): M[] {
  return STATE_MODE_IDS.flatMap((id) => (modes ?? []).filter((mode) => mode.id === id))
}

/** The modes of a row the Indicator column shows: all but those of the State column. */
export function indicatorModes<M extends ModeLike>(modes: readonly M[] | null | undefined): M[] {
  return (modes ?? []).filter((mode) => !STATE_MODE_ID_SET.has(mode.id))
}

function stateIconCount(row: RowWithStateIcons): number {
  return (
    Number(!!row.stale) +
    Number(!!row.is_flapping) +
    (row.modes ?? []).reduce((count, mode) => count + Number(STATE_MODE_ID_SET.has(mode.id)), 0)
  )
}

const COMPACT_TAG_WIDTH = 34
/** A 16 px icon in its 20 px hover box, and the gap the state cell keeps before each. */
const ICON_BOX = 20
const ICON_GAP = 4

export const STATE_COLUMN_MIN_WIDTH = 86

/** How much wider the spelled-out state label is than the compact one. */
export const SPELLED_OUT_EXTRA_WIDTH = 45

/** The width a compact state tag needs beside `icons` icons, at least the column's minimum. */
export function stateColumnWidth(icons: number): number {
  return Math.max(
    STATE_COLUMN_MIN_WIDTH,
    CELL_PADDING + COMPACT_TAG_WIDTH + icons * (ICON_GAP + ICON_BOX)
  )
}

/**
 * The most state icons a row of the listing has shown since the page loaded: the column grows
 * with them, but does not shrink on a refresh, so it does not jump while being read.
 */
export function useStateIconCount(rows: () => readonly RowWithStateIcons[]): ComputedRef<number> {
  const most = ref(0)
  // A reduce, not a spread: a listing without a limit can exceed the engine's argument limit.
  // Once the count is at its maximum, the rows are no longer read, so the watcher rests.
  watch(
    () =>
      most.value >= MAX_STATE_ICONS
        ? most.value
        : rows().reduce(
            (acc, row) => (acc >= MAX_STATE_ICONS ? acc : Math.max(acc, stateIconCount(row))),
            most.value
          ),
    (count) => {
      most.value = count
    },
    { immediate: true }
  )
  return computed(() => most.value)
}

/**
 * The State column hugging its icons and its header label; widened by the spelled-out label at
 * most.
 */
export function sizeStateColumn<T>(columns: ColumnDef<T>[], icons: number): ColumnDef<T>[] {
  return columns.map((column) =>
    columnId(column) === STATE_COLUMN_ID
      ? {
          ...column,
          minSize: stateColumnWidth(icons),
          meta: { ...column.meta, fitHeader: true, maxGrowth: SPELLED_OUT_EXTRA_WIDTH }
        }
      : column
  )
}
