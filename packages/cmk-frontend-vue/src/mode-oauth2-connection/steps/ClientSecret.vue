<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type {
  FormSpec,
  TwoColumnDictionary
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed, ref } from 'vue'

import usei18n from '@/lib/i18n'
import { immediateWatch } from '@/lib/watch.ts'

import type { CmkWizardStepProps } from '@/components/CmkWizard'
import { CmkWizardButton, CmkWizardStep } from '@/components/CmkWizard'
import CmkHeading from '@/components/typography/CmkHeading.vue'

import type { ValidationMessages } from '@/form'
import FormEdit from '@/form/FormEdit.vue'

import type { OAuth2FormData } from '@/mode-oauth2-connection/lib/service/oauth2-connection-api.ts'

import {
  filteredDataInFilteredDictionary,
  filteredDictionaryByGroupName,
  filteredValidationMessagesInFilteredDictionary
} from './utils'

const { _t } = usei18n()

const props = defineProps<
  CmkWizardStepProps & {
    formSpec: {
      id: string
      spec: FormSpec
      validation?: ValidationMessages
      data: unknown
    }
  }
>()
const model = defineModel<{ data: OAuth2FormData; validation: ValidationMessages }>({
  required: true
})

async function validate(): Promise<boolean> {
  model.value.validation = []
  if (
    model.value.data.client_secret[0] === 'explicit_password' &&
    !model.value.data.client_secret[2]
  ) {
    model.value.validation.push({
      location: ['client_secret'],
      message: _t('Client secret is required.'),
      replacement_value: ''
    })
    return false
  }
  if (
    model.value.data.client_secret[0] === 'stored_password' &&
    !model.value.data.client_secret[1]
  ) {
    model.value.validation.push({
      location: ['client_secret'],
      message: _t('Please choose a password.'),
      replacement_value: ''
    })
    return false
  }
  return true
}

const groupName = 'Secret'
const filteredDictionary = computed(() =>
  filteredDictionaryByGroupName(props.formSpec.spec as TwoColumnDictionary, groupName)
)
const filteredData = ref<Partial<OAuth2FormData>>(
  filteredDataInFilteredDictionary(model.value.data, filteredDictionary.value)
)
const filteredValidation = computed(() =>
  filteredValidationMessagesInFilteredDictionary(model.value.validation, filteredDictionary.value)
)

immediateWatch(
  () => filteredData.value,
  (newValue) => {
    model.value.data = { ...model.value.data, ...newValue }
  },
  { deep: true }
)
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading type="h2"> {{ _t('Create a new client secret') }}</CmkHeading>
    </template>

    <template #content>
      {{
        _t(
          'Navigate to Certificates & secrets. Create and copy a new client Secret to Checkmk. Please copy the client secret immediately, because it will not be shown again.'
        )
      }}
      <FormEdit
        v-model:data="filteredData"
        :backend-validation="filteredValidation"
        :spec="filteredDictionary"
      />
    </template>

    <template #actions>
      <CmkWizardButton type="next" :validation-cb="validate" />
      <CmkWizardButton type="previous" />
    </template>
  </CmkWizardStep>
</template>
