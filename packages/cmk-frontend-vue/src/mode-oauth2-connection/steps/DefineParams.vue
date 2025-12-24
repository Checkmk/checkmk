<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { type Oauth2Urls } from 'cmk-shared-typing/typescript/mode_oauth2_connection'
import type { FormSpec } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { ref } from 'vue'

import usei18n from '@/lib/i18n'

import type { CmkWizardStepProps } from '@/components/CmkWizard'
import { CmkWizardButton, CmkWizardStep } from '@/components/CmkWizard'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import type { ValidationMessages } from '@/form'

import type { OAuth2FormData } from '@/mode-oauth2-connection/lib/service/oauth2-connection-api.ts'

import FormEdit from '../../form/FormEdit.vue'

const { _t } = usei18n()

const props = defineProps<
  CmkWizardStepProps & {
    urls: Oauth2Urls
    formSpec: {
      id: string
      spec: FormSpec
      validation?: ValidationMessages
      data: unknown
    }
  }
>()

const dataRef = defineModel<OAuth2FormData>({ required: true })
const validationRef = ref<ValidationMessages>(props.formSpec.validation ?? [])

async function validate(): Promise<boolean> {
  let valid = true
  validationRef.value = []
  if (!dataRef.value.title) {
    validationRef.value.push({
      location: ['title'],
      message: _t('Title is required.'),
      replacement_value: ''
    })
    valid = false
  }
  if (!dataRef.value.tenant_id) {
    validationRef.value.push({
      location: ['tenant_id'],
      message: _t('Tenant ID is required.'),
      replacement_value: ''
    })
    valid = false
  }
  if (
    dataRef.value.tenant_id &&
    !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
      dataRef.value.tenant_id
    )
  ) {
    validationRef.value.push({
      location: ['tenant_id'],
      message: _t('Tenant ID must be a valid UUID.'),
      replacement_value: dataRef.value.tenant_id
    })
    valid = false
  }
  if (!dataRef.value.client_id) {
    validationRef.value.push({
      location: ['client_id'],
      message: _t('Client ID is required.'),
      replacement_value: ''
    })
    valid = false
  }
  if (
    dataRef.value.client_id &&
    !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
      dataRef.value.client_id
    )
  ) {
    validationRef.value.push({
      location: ['client_id'],
      message: _t('Client ID must be a valid UUID.'),
      replacement_value: dataRef.value.client_id
    })
    valid = false
  }
  return valid
}
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading type="h2"> {{ _t('Define OAuth2 parameter') }}</CmkHeading>
    </template>
    <template #content>
      <FormEdit v-model:data="dataRef" :backend-validation="validationRef" :spec="formSpec.spec" />
      <CmkParagraph>
        {{
          _t(
            'A new tab will be opened. Please follow the instructions to authorize the application.'
          )
        }}
        <br />
        {{ _t('The process has to be completed within 5 minutes.') }}
      </CmkParagraph>
    </template>

    <template #actions>
      <CmkWizardButton
        type="next"
        :override-label="_t('Start authorization')"
        :validation-cb="validate"
      />
    </template>
  </CmkWizardStep>
</template>

<style scoped>
.mode-oauth2-connection-define-params__form-row {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: var(--dimension-6);
}

.mode-oauth2-connection-define-params__label {
  display: inline-block;
  width: 120px;
}
</style>
