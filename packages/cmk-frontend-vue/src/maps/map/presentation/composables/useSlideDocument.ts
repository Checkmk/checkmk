/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import { useMaps, useStates } from '@/maps/services/context'
import type {
  MapConfig,
  PresentationElement,
  PresentationTheme,
  PresentationView
} from '@/maps/types/api'
import { newMapView } from '@/maps/utils/model'

import { clone } from '../elements'
import { useHistory } from './useHistory'

// Undo snapshots carry the theme alongside the elements so applying a template
// (which switches both) rolls back as one step.
interface DocSnapshot {
  theme: PresentationTheme
  elements: PresentationElement[]
}

const STATE_REFRESH_DELAY = 400

/**
 * The presentation editor's document model: the working copy of the view and
 * the snapshot-based undo/redo stack. All mutations funnel through ``mutate``
 * so history and persistence stay uniform no matter which panel edits the
 * slide.
 *
 * Every mutation hands the working copy to the store at once; ``MapService``
 * owns the debounce. A second window in front of it would be out of reach of
 * its flush, so leaving the map would drop the last edit.
 */
export function useSlideDocument(config: () => MapConfig, onMapSwitch?: () => void) {
  const { _t } = usei18n()
  const mapsStore = useMaps()
  const statesStore = useStates()

  function initialView(): PresentationView {
    const v = config().view
    if (v.type === 'presentation') {
      return clone(v)
    }
    return newMapView('presentation') as PresentationView
  }

  const local = ref<PresentationView>(initialView())
  const elements = computed(() => local.value.elements)

  const history = useHistory<DocSnapshot>(
    (s) => JSON.stringify(s),
    (s) => JSON.parse(s)
  )
  function currentSnapshot(): DocSnapshot {
    return { theme: local.value.theme, elements: clone(elements.value) }
  }
  function snapshot(): void {
    history.record(currentSnapshot())
  }
  function applySnapshot(s: DocSnapshot): void {
    local.value = { ...local.value, theme: s.theme, elements: s.elements }
  }

  watch(
    () => config().name,
    () => {
      local.value = initialView()
      history.reset()
      onMapSwitch?.()
    }
  )

  // A save may have (re)bound elements — fetch states rather than leaving fresh
  // bindings on PENDING until the next stream tick. Debounced on its own: most
  // edits rebind nothing, and this is a round trip.
  let refreshTimer: ReturnType<typeof setTimeout> | null = null
  function refreshStates(): void {
    if (refreshTimer) {
      clearTimeout(refreshTimer)
      refreshTimer = null
    }
    void statesStore.refresh()
  }
  function scheduleStateRefresh(): void {
    if (refreshTimer) {
      clearTimeout(refreshTimer)
    }
    refreshTimer = setTimeout(refreshStates, STATE_REFRESH_DELAY)
  }

  const unsaved = ref(false)
  const saved = ref(false)
  const saving = mapsStore.saving
  const saveLabel = computed(() => {
    if (saving.value || unsaved.value) {
      return _t('Saving…')
    }
    if (mapsStore.error.value) {
      return _t('Not saved')
    }
    return saved.value ? _t('Saved') : ''
  })

  // Only the store knows whether the slide reached the server.
  watch(saving, (now, before) => {
    if (before && !now) {
      unsaved.value = false
      saved.value = mapsStore.error.value === null
    }
  })

  function scheduleSave(): void {
    saved.value = false
    unsaved.value = true
    const map = mapsStore.currentMap.value
    if (map?.name === config().name) {
      map.view = clone(local.value)
    }
    mapsStore.scheduleSave()
    scheduleStateRefresh()
  }

  /** Persist now rather than on the debounce — the save button. */
  async function saveNow(): Promise<void> {
    scheduleSave()
    await mapsStore.flushSave()
    refreshStates()
  }

  function mutate(fn: () => void): void {
    snapshot()
    fn()
    scheduleSave()
  }
  function setElements(next: PresentationElement[]): void {
    local.value = { ...local.value, elements: next }
  }

  function undo(): void {
    const restored = history.undo(currentSnapshot())
    if (restored) {
      applySnapshot(restored)
      scheduleSave()
    }
  }
  function redo(): void {
    const restored = history.redo(currentSnapshot())
    if (restored) {
      applySnapshot(restored)
      scheduleSave()
    }
  }

  const childToGroup = computed(() => {
    const map = new Map<string, string>()
    for (const el of elements.value) {
      if (el.kind === 'group') {
        for (const c of el.children) {
          map.set(c, el.id)
        }
      }
    }
    return map
  })
  function topLevelId(id: string): string {
    return childToGroup.value.get(id) ?? id
  }
  /** Whether an element is a member of a group, and so not selectable itself. */
  function isGrouped(id: string): boolean {
    return childToGroup.value.has(id)
  }

  // Resolving an element by id is on every gesture's hot path (a connector alone
  // resolves both its ends per frame), so it goes through an index. The index
  // reads only ids, so moving an element never rebuilds it.
  const index = computed(() => new Map(elements.value.map((el) => [el.id, el])))
  function byId(id: string | null | undefined): PresentationElement | undefined {
    return id ? index.value.get(id) : undefined
  }
  // Hidden and locked cascade from a group to its members: hiding a group must
  // hide everything in it, locking it must freeze everything in it.
  function isHidden(el: PresentationElement): boolean {
    return el.hidden || !!byId(childToGroup.value.get(el.id))?.hidden
  }
  function isLocked(el: PresentationElement): boolean {
    return el.locked || !!byId(childToGroup.value.get(el.id))?.locked
  }

  const nextZ = computed(() => elements.value.reduce((m, e) => Math.max(m, e.z), 0) + 1)

  onBeforeUnmount(() => {
    if (refreshTimer) {
      clearTimeout(refreshTimer)
    }
  })

  return {
    local,
    elements,
    history,
    snapshot,
    mutate,
    setElements,
    scheduleSave,
    saveNow,
    saving,
    saveLabel,
    undo,
    redo,
    childToGroup,
    topLevelId,
    isGrouped,
    byId,
    isHidden,
    isLocked,
    nextZ
  }
}
