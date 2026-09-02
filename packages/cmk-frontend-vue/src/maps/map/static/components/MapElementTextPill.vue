<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
A monitored object shown as its name alone, coloured by its state.

Chosen where an icon would only add noise — a rack of hosts on a photo of the
rack, say, where the position already says which host it is and only the state
is news.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { MapElement, ObjectState } from '@/maps/types/api'
import { objectCaption } from '@/maps/utils/dropdownOptions'
import { stateColorVar } from '@/maps/utils/stateColors'

const { _t } = usei18n()

const props = defineProps<{
  object: MapElement
  state: ObjectState | undefined
  iconSize: number
  selected?: boolean
}>()

const configuredStyle = computed(() => {
  const label = props.object.label
  const background = label?.background
  const border = props.object.label_border
  const x = label?.x ?? 0
  const y = label?.y ?? 0
  return {
    // Without a configured size the pill scales with the icon size the map is
    // set to, so a text object sits at the same visual weight as its neighbours.
    fontSize: `${label?.size ?? Math.max(12, Math.round(props.iconSize * 0.4))}px`,
    color: label?.color ?? stateColorVar(props.state?.state),
    background: background && background !== 'transparent' ? background : undefined,
    outline: border ? `1px solid ${border}` : undefined,
    transform: x || y ? `translate(${x}px, ${y}px)` : undefined
  }
})
</script>

<template>
  <div class="maps-map-element-text-pill">
    <div
      class="maps-map-element-text-pill__body"
      :class="selected ? 'maps-map-element-text-pill__body--selected' : ''"
      :style="configuredStyle"
    >
      {{ objectCaption(object, _t) }}
    </div>
  </div>
</template>

<style scoped>
.maps-map-element-text-pill {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.maps-map-element-text-pill__body {
  padding: var(--dimension-2) 6px;
  font-weight: var(--font-weight-bold);
  white-space: nowrap;
  background: var(--maps-map-view-label-bg);
  outline: 1px solid var(--maps-map-view-hairline);
  border-radius: var(--border-radius);
  backdrop-filter: blur(4px);
  text-shadow: var(--maps-map-view-text-halo);
  pointer-events: none;
}

.maps-map-element-text-pill__body--selected {
  box-shadow:
    0 0 0 2px var(--ux-theme-1),
    0 0 0 4px var(--color-corporate-green-50);
}
</style>
