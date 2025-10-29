<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { CmkWizardButton, CmkWizardStep } from '@/components/CmkWizard'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

defineProps<{ index: number; isCompleted: () => boolean }>()
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
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
</template>
