<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { ref } from 'vue'

import CmkWizard, {
  CmkWizardButton,
  CmkWizardModeToggle,
  CmkWizardStep
} from '@/components/CmkWizard'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import StepOne from './StepOne.vue'

defineProps<{ screenshotMode: boolean }>()
const currentStep = ref(1)
const currentMode = ref<'guided' | 'overview'>('guided')
</script>

<template>
  <CmkWizardModeToggle v-model="currentMode" />
  <CmkWizard v-model="currentStep" :mode="currentMode">
    <StepOne :index="1" :is-completed="() => currentStep >= 1" />
    <CmkWizardStep :index="2" :is-completed="() => currentStep >= 2">
      <template #header>
        <CmkHeading>Step 2</CmkHeading>
      </template>
      <template #content>
        <CmkParagraph> This is the content of the second step. </CmkParagraph>
      </template>
      <template #actions>
        <CmkWizardButton type="previous" />
        <CmkWizardButton type="next" />
      </template>
    </CmkWizardStep>
    <CmkWizardStep :index="3" :is-completed="() => currentStep >= 3">
      <template #header>
        <CmkHeading>Step 3</CmkHeading>
      </template>
      <template #content>
        <CmkParagraph> This is the content of the third step. </CmkParagraph>
      </template>
      <template #actions>
        <CmkWizardButton type="previous" />
      </template>
    </CmkWizardStep>
  </CmkWizard>
</template>
