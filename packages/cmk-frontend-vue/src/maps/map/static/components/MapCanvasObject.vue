<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
One placed object on a static map: the positioned, focusable box the canvas puts
at the object's coordinates, with the object's own presentation inside it.

The box is what carries the interaction — pointer, keyboard and context menu —
and the ``data-object-id`` every gesture and the line anchors look objects up
by. What it contains is ``MapElement``'s business.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref, useTemplateRef } from 'vue'

import type { HoverAnchorRect } from '@/maps/map/composables/useObjectHoverMenu'
import MapElement from '@/maps/map/elements/MapElement.vue'
import { objectIconSize } from '@/maps/map/objectIconSize'
import { gridLayout, gridMembersOf } from '@/maps/map/static/gridMembers'
import { gridCaption } from '@/maps/map/static/gridSummary'
import type { MapConfig, MapElement as MapObject, ObjectState } from '@/maps/types/api'
import { anchorRectOf } from '@/maps/utils/anchorRect'
import { objectAriaLabel } from '@/maps/utils/objectAria'

import MapGridFrame from './MapGridFrame.vue'

const i18n = usei18n()
const { _t } = i18n

const props = defineProps<{
  object: MapObject
  /** All the map's states: the object reads its own, so a change redraws only it. */
  states: Readonly<Record<string, ObjectState>>
  config: MapConfig
  /** Icon size to use when neither object nor map names one. */
  fallbackIconSize: number
  iconSizeOverride?: number | undefined
  selected?: boolean
  editMode?: boolean
  /** Whether a line being dragged would bind to this object on release. */
  bindTarget?: boolean
  /** Live size while the operator is dragging this object's resize grip. */
  resizeOverride?: { width: number; height: number } | undefined
  /** Placement and dimming, from the canvas layout. */
  boxStyle: Record<string, string | number | undefined>
  captionWidth?: number | undefined
  /** Drawn to be looked at, not used: no tab stop, no grip. */
  displayOnly?: boolean
  tabStop?: boolean
}>()

/** The object's own box, so the hover card anchors on what was hovered. */
const root = useTemplateRef<HTMLElement>('root')

const emit = defineEmits<{
  'pointer-down': [event: PointerEvent]
  activate: [event?: MouseEvent]
  'context-menu': [event: MouseEvent]
  'double-click': [event: MouseEvent]
  hover: [event: MouseEvent, anchor: HoverAnchorRect | null]
  'hover-leave': []
  'resize-start': [event: PointerEvent]
  'grid-resize-start': [event: PointerEvent, members: number]
  'subtree-enter': [object: MapObject, state: ObjectState, event: MouseEvent]
  'subtree-leave': []
}>()

const iconSize = computed(() =>
  objectIconSize(props.object, {
    map: props.config.icon_size,
    override: props.iconSizeOverride,
    fallback: props.fallbackIconSize
  })
)

const state = computed(() => props.states[props.object.id])

const isGrid = computed(() => props.object.type === 'grid')
// A grid's box is its first slot; its frame shows the focus instead.
const gridFocused = ref(false)
function onFocus(): void {
  gridFocused.value = isGrid.value && root.value?.matches(':focus-visible') === true
}

const gridMembers = computed(() =>
  isGrid.value ? gridMembersOf(props.config.objects, props.object.id) : []
)

const spacedX = computed(() => isGrid.value && gridLayout(props.object).offsetX > 0)

const ariaLabel = computed(() =>
  isGrid.value
    ? gridCaption(i18n, props.object, state.value, gridMembers.value.length)
    : objectAriaLabel(_t, props.object, state.value?.state, state.value?.stale)
)

function onKeydown(event: KeyboardEvent): void {
  if (event.key !== 'Enter' && event.key !== ' ') {
    return
  }
  event.preventDefault()
  emit('activate')
}
</script>

<template>
  <div
    ref="root"
    class="maps-map-canvas-object"
    :class="{
      'maps-map-canvas-object--bind-target': bindTarget,
      'maps-map-canvas-object--selected': editMode && selected && !isGrid,
      'maps-map-canvas-object--grid': isGrid,
      'maps-map-canvas-object--selected-grid': editMode && selected && isGrid
    }"
    :data-object-id="object.id"
    :style="boxStyle"
    :tabindex="!displayOnly && tabStop ? 0 : -1"
    role="button"
    :aria-label="ariaLabel"
    @pointerdown="emit('pointer-down', $event)"
    @dragstart.prevent
    @click.stop="emit('activate', $event)"
    @dblclick.stop="emit('double-click', $event)"
    @keydown="onKeydown"
    @focus="onFocus"
    @blur="gridFocused = false"
    @contextmenu.prevent="emit('context-menu', $event)"
  >
    <MapGridFrame
      v-if="isGrid"
      :grid="object"
      :members="gridMembers"
      :state="state"
      :icon-size="iconSize"
      :selected="selected"
      :focused="gridFocused"
      :resizable="editMode && selected && !displayOnly && gridMembers.length > 0 && spacedX"
      @resize-start="emit('grid-resize-start', $event, gridMembers.length)"
    />
    <MapElement
      v-else
      :object="object"
      :state="state"
      :icon-size="iconSize"
      :selected="selected"
      :edit-mode="editMode"
      :resize-override="resizeOverride"
      :caption-width="captionWidth"
      :connection-id="config.connection_id"
      :render-mode="config.render_mode ?? 'default'"
      @hover="emit('hover', $event, anchorRectOf(root))"
      @hover-leave="emit('hover-leave')"
      @graph-resize-start="emit('resize-start', $event)"
      @subtree-enter="(node, nodeState, event) => emit('subtree-enter', node, nodeState, event)"
      @subtree-leave="emit('subtree-leave')"
    />
  </div>
</template>

<style scoped>
.maps-map-canvas-object {
  position: absolute;
}

.maps-map-canvas-object:focus-visible {
  outline: revert;
  outline-offset: 2px;
}

/* Lifted above its objects, the grid leaves their presses to them; its caption
   and grip take their own back. */
.maps-map-canvas-object--selected-grid {
  pointer-events: none;
}

.maps-map-canvas-object--grid:focus-visible {
  outline: none;
}

/* The object a line being dragged would bind to on release. */
.maps-map-canvas-object--bind-target {
  outline: 3px solid var(--interactive-accent);
  outline-offset: 3px;
  border-radius: var(--border-radius);
}

.maps-map-canvas-object--selected {
  outline: 2px dashed var(--interactive-accent);
  outline-offset: 4px;
  border-radius: var(--border-radius);
}
</style>
