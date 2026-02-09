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

import { CmkWizardButton, CmkWizardStep } from '@/components/CmkWizard'
import type { CmkWizardStepProps } from '@/components/CmkWizard'
import CmkHeading from '@/components/typography/CmkHeading.vue'

import type { ValidationMessages } from '@/form'
import FormEdit from '@/form/FormEdit.vue'

import type { OAuth2FormData } from '@/mode-oauth2-connection/lib/service/oauth2-connection-api.ts'

import {
  filteredDataInFilteredDictionary,
  filteredDictionaryByGroupName,
  filteredValidationMessagesInFilteredDictionary,
  isValidUUID
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
  let valid = true
  if (!model.value.data.tenant_id) {
    model.value.validation.push({
      location: ['tenant_id'],
      message: _t('Tenant ID is required.'),
      replacement_value: ''
    })
    valid = false
  }
  if (model.value.data.tenant_id && !isValidUUID(model.value.data.tenant_id)) {
    model.value.validation.push({
      location: ['tenant_id'],
      message: _t('Tenant ID must be a valid UUID.'),
      replacement_value: model.value.data.tenant_id
    })
    valid = false
  }
  if (!model.value.data.client_id) {
    model.value.validation.push({
      location: ['client_id'],
      message: _t('Client ID is required.'),
      replacement_value: ''
    })
    valid = false
  }
  if (model.value.data.client_id && !isValidUUID(model.value.data.client_id)) {
    model.value.validation.push({
      location: ['client_id'],
      message: _t('Client ID must be a valid UUID.'),
      replacement_value: model.value.data.client_id
    })
    valid = false
  }
  return valid
}

const groupName = 'IDs'
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
      <CmkHeading type="h2"> {{ _t('Copy app IDs') }}</CmkHeading>
    </template>

    <template #content>
      {{
        _t(
          'Navigate to the app overview (Essentials). Copy the Application (client) ID and Directory (tenant) ID into the fields below.'
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
