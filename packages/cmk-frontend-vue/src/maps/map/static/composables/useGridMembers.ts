/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { computed, watch } from 'vue'

import { isGridMemberId } from '@/maps/api/wire'
import {
  gridLayout,
  gridMemberElement,
  gridOrder,
  gridPosition,
  mapGrids,
  nagvisStateWeight
} from '@/maps/map/static/gridMembers'
import { useMaps, useStates } from '@/maps/services/context'
import type { MapConfig, MapElement, ObjectState } from '@/maps/types/api'
import { monitoringObjectId } from '@/maps/utils/model'

function memberKey(host: string, service: string | null | undefined): string {
  return monitoringObjectId(host, service ?? null)
}

// As the daemon leaves them out: the objects pinned out of a grid, per grid.
function pinnedKeys(map: MapConfig): Map<string, Set<string>> {
  const pinned = new Map<string, Set<string>>()
  for (const o of map.objects) {
    if (o.grid_id && o.host_name && !isGridMemberId(o.id)) {
      const keys = pinned.get(o.grid_id) ?? new Set<string>()
      keys.add(memberKey(o.host_name, o.type === 'service' ? o.service_description : null))
      pinned.set(o.grid_id, keys)
    }
  }
  return pinned
}

/**
 * How a grid's members find their slots: all anew in order, the slots kept
 * with new members appended, or the slots kept with new members in the ones
 * left free.
 */
type SlotMode = 'fresh' | 'append' | 'refill'

/**
 * Keeps the members of the open map's grids in step with the states.
 *
 * The grids are laid out again only when their members, their settings or,
 * sorted by state, their members' weights change, and a member that keeps its
 * place keeps its object, so a state change re-renders no other member.
 * While the map is edited every member keeps its slot, so nothing moves under
 * the pointer; new members join at the end. A grid whose layout or filter
 * changes is laid out anew.
 *
 * A grid sorted by name that the daemon cuts at its limit trades members as
 * their states change, problems first: a member joining takes the slot of the
 * one leaving, so the members after it stay where they are.
 */
export function useGridMembers(editing: () => boolean): void {
  const mapsStore = useMaps()
  const statesStore = useStates()
  const shown = new Map<
    string,
    { settings: string; slots: string[]; grid: string; members: MapElement[]; mode: SlotMode }
  >()
  let shownMap: string | null = null

  // A string, so laying the members out, which replaces the map's objects,
  // does not by itself call for another layout.
  const gridsKey = computed(() => JSON.stringify(mapGrids(mapsStore.currentMap.value)))
  const grids = computed(() => JSON.parse(gridsKey.value) as MapElement[])
  // What the grid's members and their order depend on; moving a grid moves them along.
  const layoutKeys = computed(
    () =>
      new Map(
        grids.value.map((grid) => [
          grid.id,
          JSON.stringify([
            gridLayout(grid),
            grid.object_types,
            grid.object_filter,
            grid.only_hard_states,
            grid.recognize_services
          ])
        ])
      )
  )

  function isCut(grid: MapElement): boolean {
    return statesStore.states.value[grid.id]?.grid_truncated === true
  }

  const statesByGrid = computed(() => {
    const byGrid = new Map<string, ObjectState[]>()
    if (grids.value.length === 0) {
      return byGrid
    }
    for (const state of Object.values(statesStore.states.value)) {
      if (state.grid_id && state.host_name) {
        const states = byGrid.get(state.grid_id) ?? []
        states.push(state)
        byGrid.set(state.grid_id, states)
      }
    }
    return byGrid
  })

  // A pin taken back shows the member again before the daemon says so.
  const pinnedKey = computed(() => {
    const map = mapsStore.currentMap.value
    if (!map || grids.value.length === 0) {
      return ''
    }
    return JSON.stringify([...pinnedKeys(map)].map(([grid, keys]) => [grid, [...keys]]))
  })

  const membersKey = computed(() =>
    grids.value
      .map((grid) => {
        const byState = gridLayout(grid).sort === 'state'
        const members = (statesByGrid.value.get(grid.id) ?? [])
          .map((s) => (byState ? `${s.object_id}=${nagvisStateWeight(s)}` : s.object_id))
          .join('\n')
        return !byState && isCut(grid) ? `cut\n${members}` : members
      })
      .join('\n\n')
  )

  watch(
    [gridsKey, membersKey, pinnedKey, editing],
    () => {
      const map = mapsStore.currentMap.value
      if (!map) {
        return
      }
      // Grid ids repeat across maps, an imported one's always.
      if (shownMap !== map.name) {
        shown.clear()
        shownMap = map.name
      }
      const members: MapElement[] = []
      const editingNow = editing()
      const pinned = pinnedKeys(map)
      for (const grid of grids.value) {
        const settings = layoutKeys.value.get(grid.id)!
        const before = shown.get(grid.id)
        const gridJson = JSON.stringify(grid)
        const layout = gridLayout(grid)
        const left = pinned.get(grid.id)
        const ordered = gridOrder(
          layout,
          (statesByGrid.value.get(grid.id) ?? []).filter(
            (state) => !left?.has(memberKey(state.host_name!, state.service_description))
          )
        )
        // While editing, members keep their slots; once the editing ends, the
        // grid is laid out anew.
        let mode: SlotMode = 'fresh'
        if (before?.settings === settings) {
          if (editingNow) {
            mode = 'append'
          } else if (layout.sort === 'name' && isCut(grid) && before.mode !== 'append') {
            mode = 'refill'
          }
        }
        const slots = before && mode !== 'fresh' ? before.slots : []
        const slot = new Map(slots.map((id, index) => [id, index]))
        const present = new Set(ordered.map((state) => state.object_id))
        // While editing, the slot of a member just pinned out stays empty; any
        // other a member left is taken again, so the grid does not creep.
        const pinnedOut = new Set(
          (mode === 'append' ? (before?.members ?? []) : [])
            .filter(
              (m) =>
                m.host_name &&
                left?.has(
                  memberKey(m.host_name, m.type === 'service' ? m.service_description : null)
                )
            )
            .map((m) => m.id)
        )
        const free =
          mode === 'fresh'
            ? []
            : slots.flatMap((id, index) => (present.has(id) || pinnedOut.has(id) ? [] : [index]))
        let nextFree = 0
        for (const state of ordered) {
          if (slot.has(state.object_id)) {
            continue
          }
          const index = free[nextFree++] ?? slots.length
          slots[index] = state.object_id
          slot.set(state.object_id, index)
        }
        // A member that keeps its place keeps its object, so it is not drawn again.
        const previous = new Map(
          before?.grid === gridJson ? before.members.map((m) => [m.id, m]) : []
        )
        const gridMembers = ordered
          .map((state) => ({ state, index: slot.get(state.object_id)! }))
          .sort((a, b) => a.index - b.index)
          .map(({ state, index }) => {
            const position = gridPosition(grid, layout, index)
            const kept = previous.get(state.object_id)
            return kept && kept.x === position.x && kept.y === position.y
              ? kept
              : gridMemberElement(grid, state, position)
          })
        shown.set(grid.id, {
          settings,
          slots,
          grid: gridJson,
          members: gridMembers,
          mode
        })
        members.push(...gridMembers)
      }
      for (const id of [...shown.keys()]) {
        if (!grids.value.some((grid) => grid.id === id)) {
          shown.delete(id)
        }
      }
      mapsStore.showGridMembers(map.name, members)
    },
    { immediate: true }
  )
}
