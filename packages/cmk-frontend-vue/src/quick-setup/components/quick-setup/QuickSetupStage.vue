<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkWizardStep from 'cmk-ui-library/components/CmkWizard/CmkWizardStep.vue'
import { computed } from 'vue'

import QuickSetupStageContent from './QuickSetupStageContent.vue'
import QuickSetupStageHeader from './QuickSetupStageHeader.vue'
import type { QuickSetupStageProps } from './quick_setup_types'

const props = defineProps<QuickSetupStageProps>()

const isCompleted = computed(() => props.index < props.currentStage)
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="() => isCompleted">
    <template #header>
      <QuickSetupStageHeader :title="title" :sub-title="sub_title" :is-completed="isCompleted" />
    </template>
    <template #content>
      <QuickSetupStageContent
        :index="index"
        :number-of-stages="numberOfStages"
        :loading="loading || isCompleted"
        :mode="mode"
        :errors="errors"
        :actions="actions"
        :content="content || null"
        :hide-wait-icon="!!hideWaitIcon"
      />
    </template>
    <template #recap>
      <div class="qs-stage__recap">
        <component :is="recapContent" v-if="!!recapContent" />
      </div>
    </template>
  </CmkWizardStep>
</template>

<style scoped>
.qs-stage__recap {
  width: 100%;
  min-width: 0;
}
</style>
