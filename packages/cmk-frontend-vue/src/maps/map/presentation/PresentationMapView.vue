<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
A map somebody designed: a slide, laid out freely, with live monitoring status
on the elements that carry a binding.

This is the map type's own view -- the editor is ``PresentationCanvas``'s. What
belongs here are the surfaces a bound element opens once the slide is being
read rather than designed: the hover card and the right-click menu. Both are
navigation only; a presentation element is not a map object anyone can edit
from here, so the menu offers no editing entries.

Unlike the canvas-based map types, the slide has no drawing surface of its own
to open those on -- its elements are plain DOM -- so this view runs the shared
state machine for them.
-->
<script setup lang="ts">
import { watch } from 'vue'

import ContextMenu from '@/maps/map/components/ContextMenu.vue'
import HoverMenu from '@/maps/map/components/HoverMenu.vue'
import { useMapObjectMenus } from '@/maps/map/composables/useMapObjectMenus'
import { useStates } from '@/maps/services/context'
import type { MapConfig, MapElement } from '@/maps/types/api'

import PresentationCanvas from './components/PresentationCanvas.vue'

const props = defineProps<{
  config: MapConfig | null
  editMode: boolean
  kiosk: boolean
  /** The settings preview is not interactive. */
  preview: boolean
  checkmkUrl: string | null
}>()

const emit = defineEmits<{
  /** A bound element was picked, for the shared object-click contract. */
  'object-click': [object: MapElement, event: MouseEvent | undefined]
}>()

const statesStore = useStates()

const menus = useMapObjectMenus({
  config: () => props.config,
  stateOf: (objectId) => statesStore.states.value[objectId],
  preview: () => props.preview
})

// The view survives map switches (rotation, breadcrumb): a hover card or
// context menu opened on the previous map must not carry over.
watch(
  () => props.config?.name,
  () => menus.close()
)

function onObjectClick(object: MapElement, event?: MouseEvent): void {
  menus.close()
  emit('object-click', object, event)
}
</script>

<template>
  <div class="maps-presentation-map-view">
    <PresentationCanvas
      v-if="config"
      :config="config"
      :states="statesStore.states.value"
      :edit-mode="editMode"
      :readonly="config.readonly ?? false"
      :preview="preview"
      :kiosk="kiosk"
      @object-hover="(obj, e) => menus.openHover(obj, e)"
      @object-hover-leave="menus.hover.scheduleClose()"
      @object-click="onObjectClick"
      @object-context="(obj, e) => menus.openContext(obj, e)"
    />

    <HoverMenu
      v-if="menus.hover.hover.visible && menus.hover.hover.object"
      :object="menus.hover.hover.object"
      :state="menus.hover.state.value"
      :x="menus.hover.hover.x"
      :y="menus.hover.hover.y"
      :anchor-rect="menus.hover.hover.anchorRect"
      :connection-id="menus.hover.hover.object.connection_id ?? config?.connection_id ?? null"
      :checkmk-url="checkmkUrl"
      :template="menus.hoverTemplate.value"
      @card-enter="menus.hover.cancelClose()"
      @card-leave="menus.hover.scheduleClose()"
    />

    <ContextMenu
      v-if="menus.context.visible && menus.context.object"
      :object="menus.context.object"
      v-bind="menus.contextState.value"
      :x="menus.context.x"
      :y="menus.context.y"
      :checkmk-url="checkmkUrl"
      :template="menus.contextTemplate.value"
      @close="menus.close()"
    />
  </div>
</template>

<style scoped>
.maps-presentation-map-view {
  position: relative;
  flex: 1 1 0%;
  display: flex;
  overflow: hidden;
}
</style>
