<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { type Oauth2Urls } from 'cmk-shared-typing/typescript/mode_oauth2_connection'
import type { FormSpec } from 'cmk-shared-typing/typescript/vue_formspec_components'

import usei18n from '@/lib/i18n'

import type { CmkWizardStepProps } from '@/components/CmkWizard'
import { CmkWizardButton, CmkWizardStep } from '@/components/CmkWizard'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import type { ValidationMessages } from '@/form'

import type { OAuth2FormData } from '@/mode-oauth2-connection/lib/service/oauth2-connection-api.ts'

import FormEdit from '../../form/FormEdit.vue'

const { _t } = usei18n()

defineProps<
  CmkWizardStepProps & {
    urls: Oauth2Urls
    form_spec: {
      id: string
      spec: FormSpec
      validation?: ValidationMessages
      data: unknown
    }
  }
>()

const dataRef = defineModel<OAuth2FormData>({ required: true })

async function validate(): Promise<boolean> {
  return true
}
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading type="h2"> {{ _t('Define OAuth2 parameter') }}</CmkHeading>
    </template>
    <template #content>
      <FormEdit
        v-model:data="dataRef"
        :backend-validation="form_spec.validation ?? []"
        :spec="form_spec.spec"
      />
      <CmkParagraph>
        {{
          _t(
            'A new tab will be opened. Please follow the instructions to authorize the application. The process has to be completed within 5 minutes.'
          )
        }}
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
