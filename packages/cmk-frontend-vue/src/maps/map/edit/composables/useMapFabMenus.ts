/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref, watch } from 'vue'

import type { MapEditor } from '@/maps/map/composables/useMapEditor'
import { snapGridSizes } from '@/maps/map/edit/draftFacts'

/**
 * What the floating edit buttons open: the panel that adds an object, and the
 * menu that sets how coarsely the canvas snaps.
 *
 * Both only hold what is open — the editor owns the draft and the grid size
 * itself. Closing is the caller's: the grid button carries `v-click-outside`,
 * and the view's Escape handler reaches the menu through `gridMenuOpen`.
 */
export function useMapFabMenus(editor: MapEditor) {
  const { _t } = usei18n()

  // ---- Add-object panel ----
  // The panel is opened by its button and closed by its own close action; a
  // click beside it must not dismiss it, because placing an object *is* a click
  // beside it. The object type is picked inside the panel, so there is no
  // second surface listing the types.
  const addPanelOpen = ref(false)

  function toggleAddPanel(): void {
    addPanelOpen.value = !addPanelOpen.value
  }

  function closeAddPanel(): void {
    addPanelOpen.value = false
    editor.resetDraft()
  }

  // Leaving edit mode dismisses the panel so it can't linger over a read-only map.
  watch(
    () => editor.editMode.value,
    (on) => {
      if (!on) {
        closeAddPanel()
      }
    }
  )

  // ---- Grid-snap menu ----
  const gridMenuOpen = ref(false)
  const gridSnapActive = computed(() => editor.snapGrid.value > 0)
  const gridSizeOptions = computed(() => snapGridSizes(_t))

  function pickGrid(value: number): void {
    editor.snapGrid.value = value
    gridMenuOpen.value = false
  }

  function closeGridMenu(): void {
    gridMenuOpen.value = false
  }

  return {
    addPanelOpen,
    toggleAddPanel,
    closeAddPanel,
    gridMenuOpen,
    gridSnapActive,
    gridSizeOptions,
    pickGrid,
    closeGridMenu
  }
}
