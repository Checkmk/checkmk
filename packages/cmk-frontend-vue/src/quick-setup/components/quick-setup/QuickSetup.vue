<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import QuickSetupStage from './QuickSetupStage.vue'
import QuickSetupSaveStage from './QuickSetupSaveStage.vue'
import type { QuickSetupProps } from './quick_setup_types'

const props = defineProps<QuickSetupProps>()
const numberOfStages = computed(() => props.regularStages.length)
const isSaveStage = computed(() => props.currentStage === numberOfStages.value)
</script>

<template>
  <ol class="quick-setup">
    <QuickSetupStage
      v-for="(stg, index) in regularStages"
      :key="index"
      :index="index"
      :current-stage="currentStage"
      :number-of-stages="numberOfStages"
      :loading="loading"
      :title="stg.title"
      :sub_title="stg.sub_title || null"
      :buttons="stg.buttons || []"
      :content="stg.content || null"
      :recap-content="stg.recapContent || null"
      :errors="stg.errors"
    />
  </ol>
  <QuickSetupSaveStage
    v-if="saveStage && isSaveStage"
    :index="numberOfStages"
    :current-stage="currentStage"
    :number-of-stages="numberOfStages"
    :loading="loading"
    :content="saveStage.content || null"
    :errors="saveStage.errors || []"
    :buttons="saveStage.buttons || []"
  />
</template>

<style scoped>
.quick-setup {
  counter-reset: stage-index;
}

.quick-setup__action {
  padding-top: 1rem;
  padding-left: 7.5rem;
  position: relative;
}

.quick-setup__loading {
  display: flex;
  align-items: center;
  padding-top: 12px;
}
</style>
