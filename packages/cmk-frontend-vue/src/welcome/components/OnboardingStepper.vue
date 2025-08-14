<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { WelcomeUrls } from 'cmk-shared-typing/typescript/welcome'
import { ref } from 'vue'
import CmkAccordionStepPanel from '@/components/CmkAccordionStepPanel/CmkAccordionStepPanel.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import usei18n from '@/lib/i18n.ts'
import CmkSpace from '@/components/CmkSpace.vue'
import { stepComponents } from './steps/stepComponents'

const { _t } = usei18n()

const props = defineProps<{
  urls: WelcomeUrls
  finishedSteps: string[]
  showHeading: boolean
}>()

const buildStepId = (step: number): string => `step-${step}`
const getFirstNotFinishedStep = (finishedStages: string[]): string[] => {
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
</script>

<template>
  <CmkHeading v-if="showHeading" type="h4">
    {{ _t('First steps with Checkmk') }}
  </CmkHeading>
  <CmkSpace />
  <CmkAccordionStepPanel v-model="openedItems">
    <component
      :is="component"
      v-for="{ component, stepNumber, stepId } in stepComponents"
      :key="stepNumber"
      :step="stepNumber"
      :urls="urls"
      :accomplished="finishedSteps.includes(stepId)"
    />
  </CmkAccordionStepPanel>
</template>

<style scoped></style>
