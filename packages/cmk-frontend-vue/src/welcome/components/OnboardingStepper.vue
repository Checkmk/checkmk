<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { WelcomeCards } from 'cmk-shared-typing/typescript/welcome'
import CmkAccordionStepPanel from 'cmk-ui-library/components/CmkAccordionStepPanel/CmkAccordionStepPanel.vue'
import CmkSpace from 'cmk-ui-library/components/CmkSpace.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { immediateWatch } from 'cmk-ui-library/lib/watch.ts'
import { ref } from 'vue'

import { stepComponents } from './steps/stepComponents'
import type { StepId } from './steps/utils'

const { _t } = usei18n()

const props = defineProps<{
  cards: WelcomeCards
  finishedSteps: StepId[]
  showHeading: boolean
}>()

const emit = defineEmits(['step-completed'])
const buildStepId = (step: number): string => `step-${step}`
const getFirstNotFinishedStep = (finishedStages: StepId[]): string[] => {
  const steps = stepComponents.map(({ stepId }) => stepId)
  const firstUnfinished = steps.find((stepId) => !finishedStages.includes(stepId))
  return firstUnfinished
    ? [
        buildStepId(
          stepComponents.find(({ stepId }) => stepId === firstUnfinished)?.stepNumber || 1
        )
      ]
    : []
}
const openedItems = ref<string[]>(getFirstNotFinishedStep(props.finishedSteps))

immediateWatch(
  () => props.finishedSteps,
  (newFinishedSteps) => {
    openedItems.value = getFirstNotFinishedStep(newFinishedSteps)
  }
)
</script>

<template>
  <CmkHeading v-if="showHeading" type="h4">
    {{ _t('Topics to explore') }}
  </CmkHeading>
  <CmkSpace />
  <CmkAccordionStepPanel v-model="openedItems" data-testid="onboarding-steps">
    <component
      :is="component"
      v-for="{ component, stepNumber, stepId } in stepComponents"
      :key="stepNumber"
      :step="stepNumber"
      :step-id="stepId"
      :cards="cards"
      :accomplished="finishedSteps.includes(stepId)"
      @step-completed="emit('step-completed', $event)"
    />
  </CmkAccordionStepPanel>
</template>
