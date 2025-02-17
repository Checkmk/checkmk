<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, provide, onMounted, onBeforeUnmount } from 'vue'

import QuickSetupStage from './QuickSetupStage.vue'
import QuickSetupSaveStage from './QuickSetupSaveStage.vue'
import type { QuickSetupProps } from './quick_setup_types'

import { getWidget } from './widgets/utils'
import { quickSetupGetWidgetKey } from './utils'
provide(quickSetupGetWidgetKey, getWidget)

const props = defineProps<QuickSetupProps>()

const numberOfStages = computed(() => props.regularStages.length)
const showSaveStage = computed(
  () => props.currentStage === numberOfStages.value || props.mode.value === 'overview'
)

onMounted(() => {
  window.addEventListener('beforeunload', handleBrowserDialog)
  // The "old" world sets the title to "Reloading..." if a reload is
  // triggered. This would lead to a wrong title in case the user clicks
  // "Cancel" in the browser dialog
  document.querySelectorAll('a.title').forEach((link) => {
    link.setAttribute('onclick', 'document.location.reload();')
  })
})

onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', handleBrowserDialog)
})

function handleBrowserDialog(event: BeforeUnloadEvent) {
  if (props.preventLeaving) {
    event.preventDefault()
    event.returnValue = ''
  }
}
</script>

<template>
  <ol class="quick-setup">
    <QuickSetupStage
      v-for="(stg, index) in regularStages"
      :key="index"
      :index="index"
      :current-stage="currentStage"
      :number-of-stages="numberOfStages"
      :mode="props.mode.value"
      :loading="loading"
      :title="stg.title"
      :sub_title="stg.sub_title || null"
      :actions="stg.actions || []"
      :content="stg.content || null"
      :recap-content="stg.recapContent || null"
      :errors="stg.errors"
      :go-to-this-stage="stg.goToThisStage || null"
      :hide-wait-legend="!!props.hideWaitLegend"
    />
  </ol>
  <QuickSetupSaveStage
    v-if="saveStage && showSaveStage"
    :index="numberOfStages"
    :current-stage="currentStage"
    :number-of-stages="numberOfStages"
    :mode="props.mode.value"
    :loading="loading"
    :content="saveStage.content || null"
    :errors="saveStage.errors || []"
    :actions="saveStage.actions || []"
    :hide-wait-legend="!!props.hideWaitLegend"
  />
</template>

<style scoped>
.quick-setup {
  margin: 8px 0 0;
  padding-left: 0;
  counter-reset: stage-index;
}
</style>
