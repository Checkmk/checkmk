<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkWizard from '@/components/CmkWizard/CmkWizard.vue'
import CmkWizardButton from '@/components/CmkWizard/CmkWizardButton.vue'
import CmkWizardStep from '@/components/CmkWizard/CmkWizardStep.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'
import { ref } from 'vue'
import CmkWizardModeToggle from '@/components/CmkWizard/CmkWizardModeToggle.vue'

defineProps<{ screenshotMode: boolean }>()
const currentStep = ref(1)
const currentMode = ref<'guided' | 'overview'>('guided')
</script>

<template>
  <CmkWizardModeToggle v-model="currentMode" />
  <CmkWizard v-model="currentStep" :mode="currentMode">
    <CmkWizardStep :index="1" :is-completed="() => currentStep >= 1">
      <template #header>
        <CmkHeading>Step 1</CmkHeading>
      </template>
      <template #content>
        <CmkParagraph> This is the content of the first step. </CmkParagraph>
      </template>
      <template #actions>
        <CmkWizardButton type="next" />
      </template>
    </CmkWizardStep>
    <CmkWizardStep :index="2" :is-completed="() => currentStep >= 2">
      <template #header>
        <CmkHeading>Step 2</CmkHeading>
      </template>
      <template #content>
        <CmkParagraph> This is the content of the second step. </CmkParagraph>
      </template>
      <template #actions>
        <CmkWizardButton type="previous" />
      </template>
    </CmkWizardStep>
  </CmkWizard>
</template>

<style scoped></style>
