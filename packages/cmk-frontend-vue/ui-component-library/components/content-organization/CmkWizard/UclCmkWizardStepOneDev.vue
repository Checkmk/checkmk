<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed, ref } from 'vue'

import CmkLabel from '@/components/CmkLabel.vue'
import { CmkWizardButton, CmkWizardStep } from '@/components/CmkWizard'
import type { CmkWizardStepProps } from '@/components/CmkWizard'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'
import CmkLabelRequired from '@/components/user-input/CmkLabelRequired.vue'

defineProps<CmkWizardStepProps>()

const checkboxChecked = ref(false)
const yourName = ref<string>('')

const displayErrors = ref(false)

const getCheckboxErrors = () => {
  const errors: string[] = []
  if (!checkboxChecked.value) {
    errors.push('This checkbox needs to be checked')
  }
  return errors
}

const getNameErrors = () => {
  const errors: string[] = []
  const name = yourName.value.trim()
  if (name.length === 0) {
    errors.push('Your name is required')
  } else if (name.length > 10) {
    errors.push('Name cannot be longer than 10 characters')
  }
  return errors
}

const checkboxErrors = computed(() => {
  return displayErrors.value ? getCheckboxErrors() : []
})

const yourNameErrors = computed(() => {
  return displayErrors.value ? getNameErrors() : []
})

async function validate(): Promise<boolean> {
  displayErrors.value = true
  return getCheckboxErrors().length === 0 && getNameErrors().length === 0
}
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
      <CmkLabel>
        Choose a name
        <CmkLabelRequired />
      </CmkLabel>
      <CmkInput
        v-model="yourName"
        type="text"
        field-size="MEDIUM"
        :external-errors="yourNameErrors"
      />
    </template>
    <template #actions>
      <CmkWizardButton type="next" :validation-cb="validate" />
    </template>
  </CmkWizardStep>
</template>
