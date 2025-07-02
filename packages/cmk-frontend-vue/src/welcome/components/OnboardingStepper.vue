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
import CmkHeading2 from '@/components/typography/CmkHeading2.vue'
import usei18n from '@/lib/i18n.ts'
import CmkSpace from '@/components/CmkSpace.vue'

const { t } = usei18n('onboarding-stepper')

defineProps<{
  urls: WelcomeUrls
}>()
const openedItems = ref<string[]>(['step-2'])
</script>

<template>
  <CmkHeading2>
    {{ t('first-steps', 'First steps with Checkmk') }}
  </CmkHeading2>
  <CmkSpace />
  <CmkAccordionStepPanel v-model="openedItems">
    <StepOne />
    <StepTwo :urls="urls" />
    <StepThree :urls="urls" />
    <StepFour :urls="urls" />
    <StepFive :urls="urls" />
  </CmkAccordionStepPanel>
</template>

<style scoped></style>
