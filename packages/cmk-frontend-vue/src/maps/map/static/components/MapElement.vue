<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
One object on a static map.

What an object looks like is a property of the object, not of the canvas, so the
choice between the five presentations lives here and the canvas only places the
result. The pointer events every presentation shares — hover, right-click, the
resize grip — are declared once, on whichever presentation is showing.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { MapElement, ObjectState } from '@/maps/types/api'
import { objectCaption } from '@/maps/utils/dropdownOptions'

import MapElementGadget from './MapElementGadget.vue'
import MapElementGraph from './MapElementGraph.vue'
import MapElementIcon from './MapElementIcon.vue'
import MapElementLabel from './MapElementLabel.vue'
import MapElementTextPill from './MapElementTextPill.vue'
import MapElementTextbox from './MapElementTextbox.vue'

const { _t } = usei18n()

const CLASSIC_DEFAULT_ICON_SIZE = 60

const props = defineProps<{
  object: MapElement
  state: ObjectState | undefined
  iconSize: number
  selected?: boolean
  editMode?: boolean
  /** Live size while the operator is dragging the resize grip. */
  resizeOverride?: { width: number; height: number } | undefined
  connectionId?: string | undefined
  renderMode?: 'default' | 'nagvis_classic'
}>()

const emit = defineEmits<{
  hover: [event: MouseEvent]
  'hover-leave': []
  'context-menu': [event: MouseEvent]
  'graph-resize-start': [event: PointerEvent]
  'subtree-enter': [object: MapElement, state: ObjectState, event: MouseEvent]
  'subtree-leave': []
}>()

const classic = computed(() => props.renderMode === 'nagvis_classic')

const kind = computed(() => {
  if (props.object.type === 'graph') {
    return 'graph'
  }
  if (props.object.type === 'textbox') {
    return 'textbox'
  }
  const mode = props.object.display?.mode
  return mode === 'gadget' || mode === 'text' ? mode : 'icon'
})

/**
 * The classic renderer pins an object's icon to its top-left corner, so the
 * stack is clamped to the icon's width — otherwise a wider caption would
 * stretch it and push the icon right.
 */
const stackStyle = computed(() => {
  if (!classic.value) {
    return undefined
  }
  const size = props.object.display?.image_size ?? props.iconSize ?? CLASSIC_DEFAULT_ICON_SIZE
  return { width: `${size}px` }
})

const showsCaption = computed(
  () => props.object.label?.show === true && props.state?.state !== 'NO_PERMISSION'
)
</script>

<template>
  <MapElementGraph
    v-if="kind === 'graph'"
    :object="object"
    :state="state"
    :selected="selected"
    :edit-mode="editMode"
    :resize-override="resizeOverride"
    :connection-id="connectionId"
    :classic="classic"
    @mouseenter="emit('hover', $event)"
    @mouseleave="emit('hover-leave')"
    @contextmenu.prevent="emit('context-menu', $event)"
    @resize-start="emit('graph-resize-start', $event)"
  />

  <MapElementTextbox
    v-else-if="kind === 'textbox'"
    :object="object"
    :selected="selected"
    :edit-mode="editMode"
    :resize-override="resizeOverride"
    :classic="classic"
    @mouseenter="emit('hover', $event)"
    @mouseleave="emit('hover-leave')"
    @contextmenu.prevent="emit('context-menu', $event)"
    @resize-start="emit('graph-resize-start', $event)"
  />

  <MapElementGadget
    v-else-if="kind === 'gadget'"
    :object="object"
    :state="state"
    :icon-size="iconSize"
    :selected="selected"
    :connection-id="connectionId"
    :classic="classic"
    @mouseenter="emit('hover', $event)"
    @mouseleave="emit('hover-leave')"
    @contextmenu.prevent="emit('context-menu', $event)"
  />

  <MapElementTextPill
    v-else-if="kind === 'text'"
    :object="object"
    :state="state"
    :icon-size="iconSize"
    :selected="selected"
    @mouseenter="emit('hover', $event)"
    @mouseleave="emit('hover-leave')"
    @contextmenu.prevent="emit('context-menu', $event)"
  />

  <div
    v-else
    class="maps-map-element"
    :class="classic ? 'maps-map-element--classic' : ''"
    :style="stackStyle"
    @mouseenter="emit('hover', $event)"
    @mouseleave="emit('hover-leave')"
    @contextmenu.prevent="emit('context-menu', $event)"
  >
    <MapElementIcon
      :object="object"
      :state="state"
      :icon-size="iconSize"
      :selected="selected"
      :connection-id="connectionId"
      :classic="classic"
      @subtree-enter="(node, nodeState, event) => emit('subtree-enter', node, nodeState, event)"
      @subtree-leave="emit('subtree-leave')"
    />
    <MapElementLabel
      v-if="showsCaption"
      :object="object"
      :text="objectCaption(object, _t)"
      placement="stacked"
      :classic="classic"
    />
  </div>
</template>

<style scoped>
.maps-map-element {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.maps-map-element--classic {
  position: relative;
}
</style>
