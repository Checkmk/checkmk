<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The floating controls that put a map into edit mode and keep it there: the
add-object panel, the grid-size menu, and the buttons that open them.

They sit over the map rather than in the page chrome, because editing is about
the canvas — and they are the only chrome an operator needs while placing
objects.
-->
<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import usei18n from 'cmk-ui-library/lib/i18n'
import useClickOutside from 'cmk-ui-library/lib/useClickOutside'
import { computed, useTemplateRef } from 'vue'

import type { MapEditor } from '@/maps/map/composables/useMapEditor'
import EditPanel from '@/maps/map/edit/EditPanel.vue'
import MapEditMenu, { type MapEditMenuEntry } from '@/maps/map/edit/components/MapEditMenu.vue'
import { useMapEditShortcuts } from '@/maps/map/edit/composables/useMapEditShortcuts'
import { useMapFabMenus } from '@/maps/map/edit/composables/useMapFabMenus'

const props = defineProps<{
  editor: MapEditor
  connectionId: string
  /** Presentation maps place elements on their slides, not via this panel. */
  offersAddObject: boolean
  /** A geo map snaps to coordinates, so it has no grid to size. */
  offersGrid: boolean
  /** False while a dialog over the map owns the keyboard. */
  keyboardActive: boolean
}>()

const emit = defineEmits<{
  'start-placing': []
  'toggle-edit-mode': []
  'delete-selection': []
  'duplicate-selection': []
}>()

// The editor is a single object owned by the map view and shared by reference:
// these controls drive it in place rather than round-tripping every keystroke
// back through the view. Aliased so that reads as the contract it is.
const editor = props.editor

const { _t } = usei18n()

const vClickOutside = useClickOutside()

const {
  addPanelOpen,
  toggleAddPanel,
  closeAddPanel,
  gridMenuOpen,
  gridSnapActive,
  gridSizeOptions,
  pickGrid,
  closeGridMenu
} = useMapFabMenus(props.editor)

const addButton = useTemplateRef<HTMLButtonElement>('addButton')
const gridButton = useTemplateRef<HTMLButtonElement>('gridButton')

/** Closing the form hands the focus back to the button that opened it. */
function dismissAddPanel(): void {
  closeAddPanel()
  addButton.value?.focus()
}

/**
 * Dismiss the grid menu and put the focus back on the button that opened it —
 * otherwise Escape drops a keyboard user out of the controls entirely.
 *
 * The add-object panel is deliberately not dismissed here: it is a form, and a
 * stray Escape while filling one in must not throw the draft away.
 *
 * Escape is owned by ``useMapEditShortcuts`` alone: a second handler on the
 * anchor would close the menu before the shortcut sees it, and the shortcut
 * would go on to clear the selection in the same keystroke.
 */
function dismissMenus(): boolean {
  if (!gridMenuOpen.value) {
    return false
  }
  closeGridMenu()
  gridButton.value?.focus()
  return true
}

useMapEditShortcuts(props.editor, {
  acceptsKeys: () => props.keyboardActive,
  closeMenus: dismissMenus,
  deleteSelection: () => emit('delete-selection'),
  duplicateSelection: () => emit('duplicate-selection')
})

const editing = computed(() => props.editor.editMode.value)

const gridEntries = computed<MapEditMenuEntry[]>(() =>
  gridSizeOptions.value.map((option) => ({
    key: String(option.value),
    title: option.title,
    active: props.editor.snapGrid.value === option.value
  }))
)
</script>

<template>
  <div class="maps-map-edit-tools">
    <Transition
      enter-from-class="maps-map-edit-tools__pop-enter-from"
      enter-active-class="maps-map-edit-tools__pop-enter-active"
      leave-to-class="maps-map-edit-tools__pop-leave-to"
      leave-active-class="maps-map-edit-tools__pop-leave-active"
      @after-leave="editor.resetDraft()"
    >
      <div v-if="editing && addPanelOpen && offersAddObject" class="maps-map-edit-tools__panel">
        <EditPanel
          v-model:draft="editor.draft"
          :placing="editor.placing.value"
          :connection-id="connectionId"
          @start-placing="emit('start-placing')"
          @cancel-add="dismissAddPanel"
        />
      </div>
    </Transition>

    <Transition
      enter-from-class="maps-map-edit-tools__pop-enter-from"
      enter-active-class="maps-map-edit-tools__pop-enter-active"
      leave-to-class="maps-map-edit-tools__pop-leave-to"
      leave-active-class="maps-map-edit-tools__pop-leave-active"
    >
      <div v-if="editing && !editor.placing.value && offersAddObject">
        <button
          ref="addButton"
          type="button"
          class="maps-map-edit-tools__button maps-map-edit-tools__button--primary"
          :title="_t('Add object')"
          :aria-label="_t('Add object')"
          :aria-expanded="addPanelOpen"
          @click="toggleAddPanel"
        >
          <CmkIcon name="add" size="medium" />
        </button>
      </div>
    </Transition>

    <div
      v-if="editing && offersGrid"
      v-click-outside="closeGridMenu"
      class="maps-map-edit-tools__anchor"
    >
      <button
        ref="gridButton"
        type="button"
        class="maps-map-edit-tools__button"
        :class="
          gridSnapActive
            ? 'maps-map-edit-tools__button--active'
            : 'maps-map-edit-tools__button--idle'
        "
        :title="_t('Grid')"
        :aria-label="_t('Grid')"
        :aria-expanded="gridMenuOpen"
        aria-haspopup="menu"
        @click="gridMenuOpen = !gridMenuOpen"
      >
        <CmkIcon name="dashboard-grid" size="medium" />
      </button>
      <Transition
        enter-from-class="maps-map-edit-tools__menu-enter-from"
        enter-active-class="maps-map-edit-tools__menu-enter-active"
        leave-to-class="maps-map-edit-tools__menu-leave-to"
        leave-active-class="maps-map-edit-tools__menu-leave-active"
      >
        <MapEditMenu
          v-if="gridMenuOpen"
          :label="_t('Grid')"
          :entries="gridEntries"
          choice
          @pick="pickGrid(Number($event))"
        />
      </Transition>
    </div>

    <button
      type="button"
      class="maps-map-edit-tools__button"
      :class="editing ? 'maps-map-edit-tools__button--active' : 'maps-map-edit-tools__button--idle'"
      :title="editing ? _t('Editing') : _t('Edit')"
      :aria-label="editing ? _t('Editing') : _t('Edit')"
      :aria-pressed="editing"
      @click="emit('toggle-edit-mode')"
    >
      <CmkIcon name="edit" size="medium" />
    </button>
  </div>
</template>

<style scoped>
/* Bounded top and bottom so the panel can only ever be as tall as the space the
   buttons leave it — the column is the constraint, rather than a constant here
   guessing at the height of what sits below the panel. The full-height strip
   this creates lets clicks through; the controls themselves take them back, so
   the map stays clickable beside them. */
.maps-map-edit-tools {
  position: fixed;
  top: var(--dimension-8);
  right: var(--dimension-8);
  bottom: var(--dimension-8);
  z-index: 40;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  justify-content: flex-end;
  gap: var(--spacing);
  pointer-events: none;
}

.maps-map-edit-tools > * {
  pointer-events: auto;
}

/* Everything but the panel keeps its size; the panel is the one that gives way. */
.maps-map-edit-tools > *:not(.maps-map-edit-tools__panel) {
  flex-shrink: 0;
}

.maps-map-edit-tools__anchor {
  position: relative;
}

.maps-map-edit-tools__panel {
  display: flex;

  /* Shrinks to the height left over, with its own field list scrolling inside. */
  flex-direction: column;
  min-height: 0;

  /* Wide enough for a label above each control rather than only inside it. */
  width: 300px;
  background: var(--ux-theme-3);
  border-radius: var(--border-radius);
  box-shadow:
    0 0 0 1px var(--default-border-color),
    0 25px 50px -12px rgb(0 0 0 / 60%);
}

.maps-map-edit-tools__button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: var(--border-radius);
  transition: all 0.2s;
}

.maps-map-edit-tools__button:active {
  transform: scale(0.95);
}

.maps-map-edit-tools__button--primary {
  background: var(--color-corporate-green-50);
  box-shadow:
    0 10px 15px -3px rgb(0 0 0 / 30%),
    0 4px 6px -4px rgb(0 0 0 / 30%);
}

.maps-map-edit-tools__button--active {
  background: var(--default-form-element-bg-color);
  box-shadow:
    0 0 0 1px var(--default-border-color),
    0 10px 15px -3px rgb(0 0 0 / 30%),
    0 4px 6px -4px rgb(0 0 0 / 30%);
}

.maps-map-edit-tools__button--idle {
  background: var(--ux-theme-3);
  box-shadow:
    0 0 0 1px var(--default-border-color),
    0 10px 15px -3px rgb(0 0 0 / 30%),
    0 4px 6px -4px rgb(0 0 0 / 30%);
}

.maps-map-edit-tools__button--idle:hover {
  background: var(--input-hover-bg-color);
}

.maps-map-edit-tools__pop-enter-from,
.maps-map-edit-tools__pop-leave-to {
  opacity: 0;
  transform: translateY(16px) scaleX(0.95) scaleY(0.75);
}

.maps-map-edit-tools__pop-enter-active {
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  transform-origin: bottom right;
}

.maps-map-edit-tools__pop-leave-active {
  transition: all 0.2s cubic-bezier(0.4, 0, 1, 1);
  transform-origin: bottom right;
}

.maps-map-edit-tools__menu-enter-from,
.maps-map-edit-tools__menu-leave-to {
  opacity: 0;
  transform: translateY(4px) scale(0.95);
}

.maps-map-edit-tools__menu-enter-active {
  transition: all 0.15s cubic-bezier(0, 0, 0.2, 1);
  transform-origin: bottom right;
}

.maps-map-edit-tools__menu-leave-active {
  transition: all 0.1s cubic-bezier(0.4, 0, 1, 1);
  transform-origin: bottom right;
}
</style>
