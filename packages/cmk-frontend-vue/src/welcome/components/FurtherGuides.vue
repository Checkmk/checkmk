<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { WelcomeCards } from 'cmk-shared-typing/typescript/welcome'
import CmkAccordionStepPanel from 'cmk-ui-library/components/CmkAccordionStepPanel/CmkAccordionStepPanel.vue'
import { computed, ref } from 'vue'

import { furtherGuideComponents } from './steps/stepComponents'
import type { StepId } from './steps/utils'

const props = defineProps<{
  cards: WelcomeCards
  finishedSteps: StepId[]
  show: 'open' | 'done'
}>()

const emit = defineEmits<{ 'step-completed': [stepId: StepId] }>()

const guides = computed(() =>
  furtherGuideComponents.filter(
    ({ stepId }) => props.finishedSteps.includes(stepId) === (props.show === 'done')
  )
)
const openedItems = ref<string[]>([])
</script>

<template>
  <CmkAccordionStepPanel v-if="guides.length > 0" v-model="openedItems">
    <component
      :is="component"
      v-for="{ component, stepNumber, stepId } in guides"
      :key="stepId"
      :step="stepNumber"
      :step-id="stepId"
      :cards="cards"
      :accomplished="show === 'done'"
      @step-completed="emit('step-completed', $event)"
    />
  </CmkAccordionStepPanel>
</template>
