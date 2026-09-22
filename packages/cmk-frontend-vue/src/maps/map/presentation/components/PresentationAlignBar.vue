<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Line several selected elements up on one edge, or even out the gaps between
them. Appears only with more than one element selected, below the insert
palette.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'

import type { AlignMode } from '../alignment'
import { ICONS } from '../chrome'
import PresentationPanel from './PresentationPanel.vue'
import PresentationToolButton from './PresentationToolButton.vue'

const { _t } = usei18n()

defineProps<{
  /** Evening out gaps needs a third element to move between the outer two. */
  canDistribute: boolean
}>()

const emit = defineEmits<{
  align: [mode: AlignMode]
  distribute: [axis: 'x' | 'y']
}>()

const ALIGN_MODES: { mode: AlignMode; icon: string; title: string }[] = [
  { mode: 'left', icon: ICONS.alignL, title: _t('Align left') },
  { mode: 'center', icon: ICONS.alignC, title: _t('Align center') },
  { mode: 'right', icon: ICONS.alignR, title: _t('Align right') },
  { mode: 'top', icon: ICONS.alignT, title: _t('Align top') },
  { mode: 'middle', icon: ICONS.alignM, title: _t('Align middle') },
  { mode: 'bottom', icon: ICONS.alignB, title: _t('Align bottom') }
]
const DISTRIBUTE_AXES: { axis: 'x' | 'y'; icon: string; title: string }[] = [
  { axis: 'x', icon: ICONS.distH, title: _t('Distribute horizontally') },
  { axis: 'y', icon: ICONS.distV, title: _t('Distribute vertically') }
]
</script>

<template>
  <PresentationPanel class="maps-presentation-align-bar">
    <PresentationToolButton
      v-for="action in ALIGN_MODES"
      :key="action.mode"
      :icon="action.icon"
      :title="action.title"
      @click="emit('align', action.mode)"
    />
    <PresentationToolButton
      v-for="action in DISTRIBUTE_AXES"
      :key="action.axis"
      :icon="action.icon"
      :title="action.title"
      :disabled="!canDistribute"
      @click="emit('distribute', action.axis)"
    />
  </PresentationPanel>
</template>

<style scoped>
.maps-presentation-align-bar {
  position: absolute;
  top: 56px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: var(--dimension-3);
  padding: var(--spacing-half);
  z-index: 5;
  animation: maps-presentation-align-bar-pop 0.12s ease-out;
}

@keyframes maps-presentation-align-bar-pop {
  from {
    opacity: 0;
    transform: translate(-50%, 6px);
  }

  to {
    opacity: 1;
    transform: translate(-50%, 0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .maps-presentation-align-bar {
    animation: none;
  }
}
</style>
