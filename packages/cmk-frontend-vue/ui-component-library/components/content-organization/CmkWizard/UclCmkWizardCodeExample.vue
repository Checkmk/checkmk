<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
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

const step = ref(1)
const mode = ref<'guided' | 'overview'>('guided')
</script>

<template>
  <CmkWizardModeToggle v-model="mode" />

  <CmkWizard v-model="step" :mode="mode">
    <CmkWizardStep :index="1" :is-completed="() => step > 1">
      <template #header><CmkHeading type="h3">Step 1: Introduction</CmkHeading></template>
      <template #content
        ><p>Welcome to the setup wizard. Please provide your initial details.</p></template
      >
      <template #actions><CmkWizardButton type="next" /></template>
    </CmkWizardStep>

    <CmkWizardStep :index="2" :is-completed="() => step > 2">
      <template #header><CmkHeading type="h3">Step 2: Configuration</CmkHeading></template>
      <template #content><p>Adjust the parameters for your monitoring instance here.</p></template>
      <template #actions>
        <CmkWizardButton type="previous" />
        <CmkWizardButton type="next" />
      </template>
    </CmkWizardStep>

    <CmkWizardStep :index="3" :is-completed="() => step > 3">
      <template #header><CmkHeading type="h3">Step 3: Review</CmkHeading></template>
      <template #content
        ><p>Verify that all settings are correct before finishing the process.</p></template
      >
      <template #actions>
        <CmkWizardButton type="previous" />
        <CmkWizardButton type="next" label="Complete Setup" />
      </template>
    </CmkWizardStep>
  </CmkWizard>
</template>
