<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Step back and forth through the slide's edit history, for operators who would
rather click than reach for Ctrl+Z.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'

import { ICONS } from '../chrome'
import PresentationPanel from './PresentationPanel.vue'
import PresentationToolButton from './PresentationToolButton.vue'

const { _t } = usei18n()

defineProps<{ canUndo: boolean; canRedo: boolean }>()

const emit = defineEmits<{ undo: []; redo: [] }>()
</script>

<template>
  <PresentationPanel class="maps-presentation-history-bar">
    <PresentationToolButton
      :icon="ICONS.undo"
      :title="_t('Undo')"
      :disabled="!canUndo"
      @click="emit('undo')"
    />
    <PresentationToolButton
      :icon="ICONS.redo"
      :title="_t('Redo')"
      :disabled="!canRedo"
      @click="emit('redo')"
    />
  </PresentationPanel>
</template>

<style scoped>
.maps-presentation-history-bar {
  position: absolute;
  bottom: 12px;
  left: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: var(--spacing-half);
  z-index: 5;
}
</style>
