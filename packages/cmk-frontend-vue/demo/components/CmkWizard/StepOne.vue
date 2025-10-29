<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { ref, watch } from 'vue'

import { CmkWizardButton, CmkWizardStep } from '@/components/CmkWizard'
import type { CmkWizardStepProps } from '@/components/CmkWizard'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

defineProps<CmkWizardStepProps>()

const checkboxChecked = ref(false)
const checkboxErrors = ref<string[]>([])

async function validate(): Promise<boolean> {
  const isValid = checkboxChecked.value

  if (!isValid) {
    checkboxErrors.value = ['This checkbox needs to be checked']
  } else {
    checkboxErrors.value = []
  }

  return isValid
}

watch(checkboxChecked, (newValue) => {
  if (newValue) {
    checkboxErrors.value = []
  }
})
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading>Step 1</CmkHeading>
    </template>
    <template #content>
      <CmkParagraph> This is the content of the first step. </CmkParagraph>
      <CmkCheckbox
        v-model="checkboxChecked"
        label="This checkbox needs to be checked to proceed."
        :external-errors="checkboxErrors"
      />
    </template>
    <template #actions>
      <CmkWizardButton type="next" :validation-cb="validate" />
    </template>
  </CmkWizardStep>
</template>
