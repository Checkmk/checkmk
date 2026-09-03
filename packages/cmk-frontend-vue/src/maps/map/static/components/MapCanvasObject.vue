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
import { computed, useTemplateRef } from 'vue'

import type { HoverAnchorRect } from '@/maps/map/composables/useObjectHoverMenu'
import MapElement from '@/maps/map/elements/MapElement.vue'
import { objectIconSize } from '@/maps/map/objectIconSize'
import type { MapConfig, MapElement as MapObject, ObjectState } from '@/maps/types/api'
import { anchorRectOf } from '@/maps/utils/anchorRect'
import { objectAriaLabel } from '@/maps/utils/objectAria'

const { _t } = usei18n()

const props = defineProps<{
  object: MapObject
  state: ObjectState | undefined
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
  /** The settings preview is not interactive. */
  preview?: boolean
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
      'maps-map-canvas-object--selected': editMode && selected
    }"
    :data-object-id="object.id"
    :style="boxStyle"
    :tabindex="preview ? -1 : 0"
    role="button"
    :aria-label="objectAriaLabel(_t, object, state?.state)"
    @pointerdown="emit('pointer-down', $event)"
    @dragstart.prevent
    @click.stop="emit('activate', $event)"
    @dblclick.stop="emit('double-click', $event)"
    @keydown="onKeydown"
    @contextmenu.prevent="emit('context-menu', $event)"
  >
    <MapElement
      :object="object"
      :state="state"
      :icon-size="iconSize"
      :selected="selected"
      :edit-mode="editMode"
      :resize-override="resizeOverride"
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
  outline: 2px solid var(--color-corporate-green-50);
  outline-offset: 2px;
}

/* The object a line being dragged would bind to on release. */
.maps-map-canvas-object--bind-target {
  outline: 3px solid var(--color-corporate-green-50);
  outline-offset: 3px;
  border-radius: 8px;
}

.maps-map-canvas-object--selected {
  outline: 2px dashed var(--color-corporate-green-50);
  outline-offset: 4px;
  border-radius: 6px;
}
</style>
