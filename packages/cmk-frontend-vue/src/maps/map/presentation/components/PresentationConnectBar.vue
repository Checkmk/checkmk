<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
How far the connect-data walkthrough has got, and the way through the remaining
slots. It replaces the insert palette while the walkthrough runs, so designing
and connecting never compete for the same corner of the canvas.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkProgressbar from 'cmk-ui-library/components/progress/CmkProgressbar.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import { ICONS } from '../chrome'
import PresentationPanel from './PresentationPanel.vue'
import PresentationToolButton from './PresentationToolButton.vue'

const { _t } = usei18n()

defineProps<{ bound: number; total: number }>()

const emit = defineEmits<{ previous: []; next: []; done: [] }>()
</script>

<template>
  <PresentationPanel class="maps-presentation-connect-bar">
    <span class="maps-presentation-connect-bar__progress">
      {{ _t('%{bound} of %{total} connected', { bound: String(bound), total: String(total) }) }}
    </span>
    <CmkProgressbar
      class="maps-presentation-connect-bar__progressbar"
      size="small"
      :value="bound"
      :max="total"
    />
    <PresentationToolButton
      :icon="ICONS.previous"
      :title="_t('Previous slot')"
      @click="emit('previous')"
    />
    <PresentationToolButton :icon="ICONS.next" :title="_t('Next slot')" @click="emit('next')" />
    <CmkButton variant="primary" size="small" @click="emit('done')">
      {{ _t('Done') }}
    </CmkButton>
  </PresentationPanel>
</template>

<style scoped>
.maps-presentation-connect-bar {
  position: absolute;
  top: 12px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  padding: 6px 10px;
  color: var(--font-color);
  z-index: 6;
}

.maps-presentation-connect-bar__progress {
  font-size: var(--font-size-normal);
  white-space: nowrap;
}

.maps-presentation-connect-bar__progressbar {
  width: 120px;
}
</style>
