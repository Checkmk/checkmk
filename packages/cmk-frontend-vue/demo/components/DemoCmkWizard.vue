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

defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  <CmkWizard mode="overview">
    <CmkWizardStep>
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
    <CmkWizardStep>
      <template #header>
        <CmkHeading>Step 2</CmkHeading>
      </template>
      <template #content>
        <CmkParagraph> This is the content of the second step. </CmkParagraph>
      </template>
      <template #actions> </template>
    </CmkWizardStep>
  </CmkWizard>
</template>

<style scoped></style>
