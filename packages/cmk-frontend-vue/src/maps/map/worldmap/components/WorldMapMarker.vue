<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
One placed object on a geo map: the focusable box inside the Leaflet marker,
with the object's own presentation inside it.

The counterpart of ``MapCanvasObject`` on a static map, and deliberately as thin
as that one: an object looks the same wherever it is placed, so what it shows is
``MapElement``'s business. Only the placement differs — Leaflet positions the
marker this box lives in, which is why the box carries no coordinates of its own.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { useTemplateRef } from 'vue'

import type { HoverAnchorRect } from '@/maps/map/composables/useObjectHoverMenu'
import MapElement from '@/maps/map/elements/MapElement.vue'
import type { MapElement as MapObject, ObjectState } from '@/maps/types/api'
import { anchorRectOf } from '@/maps/utils/anchorRect'
import { objectAriaLabel } from '@/maps/utils/objectAria'
import { dimmedStyle } from '@/maps/utils/objectFilter'

const { _t } = usei18n()

defineProps<{
  object: MapObject
  state: ObjectState | undefined
  iconSize: number
  selected: boolean
  editMode: boolean
  /** Live size while the operator is dragging this object's resize grip. */
  resizeOverride?: { width: number; height: number } | undefined
  connectionId?: string | undefined
  /** Search or the problems-only toggle is on and this object does not match. */
  dimmed: boolean
  /** The settings preview is not interactive. */
  preview: boolean
}>()

const emit = defineEmits<{
  activate: [event?: MouseEvent]
  'double-click': [event: MouseEvent]
  'context-menu': [event: MouseEvent]
  hover: [event: MouseEvent, anchor: HoverAnchorRect | null]
  'hover-leave': []
  'resize-start': [event: PointerEvent]
  'subtree-enter': [object: MapObject, state: ObjectState, event: MouseEvent]
  'subtree-leave': []
}>()

/** The marker's own box, so the hover card anchors on what was hovered. */
const root = useTemplateRef<HTMLElement>('root')

function onKeydown(event: KeyboardEvent): void {
  if (event.key !== 'Enter' && event.key !== ' ') {
    return
  }
  event.preventDefault()
  emit('activate')
}

/**
 * Leaflet drags the marker off its own ``mousedown``, so the resize grip has to
 * keep that one press to itself: ``pointerdown`` comes first, which is where the
 * grip is claimed, and the ``mousedown`` that follows for the same press is
 * stopped where it lands, before it reaches the marker.
 */
function onResizeStart(event: PointerEvent): void {
  ;(event.target as HTMLElement | null)?.addEventListener(
    'mousedown',
    (mouse: Event) => mouse.stopPropagation(),
    { once: true }
  )
  emit('resize-start', event)
}
</script>

<template>
  <div
    ref="root"
    class="maps-world-map-marker"
    :class="{ 'maps-world-map-marker--selected': selected }"
    :style="dimmedStyle(dimmed)"
    :data-object-id="object.id"
    :tabindex="preview ? -1 : 0"
    role="button"
    :aria-label="objectAriaLabel(_t, object, state?.state)"
    @click.stop="emit('activate', $event)"
    @dblclick.stop="emit('double-click', $event)"
    @contextmenu.prevent.stop="emit('context-menu', $event)"
    @keydown="onKeydown"
    @dragstart.prevent
  >
    <!-- No ``render-mode``: the NagVis-compatible renderer draws for an imported
         static map, and there is no such thing as an imported geo map. -->
    <MapElement
      :object="object"
      :state="state"
      :icon-size="iconSize"
      :selected="selected"
      :edit-mode="editMode"
      :resize-override="resizeOverride"
      :connection-id="connectionId"
      @hover="emit('hover', $event, anchorRectOf(root))"
      @hover-leave="emit('hover-leave')"
      @graph-resize-start="onResizeStart"
      @subtree-enter="(node, nodeState, event) => emit('subtree-enter', node, nodeState, event)"
      @subtree-leave="emit('subtree-leave')"
    />
  </div>
</template>

<style scoped>
.maps-world-map-marker:focus-visible {
  outline: 2px solid var(--color-corporate-green-50);
  outline-offset: 2px;
}

/* The static map's dashed selection outline, plus a white ring and a dark glow
   between marker and dashes: a marker is state-coloured, often in the same
   green as the dashes, and sits on map tiles of any colour. */
.maps-world-map-marker--selected {
  border-radius: 9px;
  outline: 3px dashed var(--color-corporate-green-50);
  outline-offset: 5px;
  box-shadow:
    0 0 0 4px var(--white),
    0 0 0 7px rgb(0 0 0 / 80%),
    0 0 14px 5px rgb(0 0 0 / 55%);
}
</style>
