<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { WelcomeUrls } from 'cmk-shared-typing/typescript/welcome'
import { ref } from 'vue'
import StepOne from '@/welcome/components/steps/StepOne.vue'
import StepTwo from '@/welcome/components/steps/StepTwo.vue'
import StepThree from '@/welcome/components/steps/StepThree.vue'
import StepFour from '@/welcome/components/steps/StepFour.vue'
import StepFive from '@/welcome/components/steps/StepFive.vue'
import CmkAccordionStepPanel from '@/components/CmkAccordionStepPanel/CmkAccordionStepPanel.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import usei18n from '@/lib/i18n.ts'
import CmkSpace from '@/components/CmkSpace.vue'

const { t } = usei18n('onboarding-stepper')

const props = defineProps<{
  urls: WelcomeUrls
  finishedSteps: number[]
  totalSteps: number
}>()

const buildStepId = (step: number): string => `step-${step}`
const getFirstNotFinishedStep = (finishedStages: number[], totalSteps: number): string[] => {
  const steps = Array.from({ length: totalSteps }, (_, i) => i + 1)
  const firstUnfinished = steps.find((step) => !finishedStages.includes(step))
  return firstUnfinished ? [buildStepId(firstUnfinished)] : []
}
const openedItems = ref<string[]>(getFirstNotFinishedStep(props.finishedSteps, props.totalSteps))
</script>

<template>
  <CmkHeading type="h2">
    {{ t('first-steps', 'First steps with Checkmk') }}
  </CmkHeading>
  <CmkSpace />
  <CmkAccordionStepPanel v-model="openedItems">
    <StepOne />
    <StepTwo :urls="urls" :accomplished="finishedSteps.includes(2)" />
    <StepThree :urls="urls" :accomplished="finishedSteps.includes(3)" />
    <StepFour :urls="urls" :accomplished="finishedSteps.includes(4)" />
    <StepFive :urls="urls" :accomplished="finishedSteps.includes(5)" />
  </CmkAccordionStepPanel>
</template>

<style scoped></style>
