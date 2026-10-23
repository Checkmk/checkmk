<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { type Oauth2Urls } from 'cmk-shared-typing/typescript/mode_oauth2_connection'
import type {
  FormSpec,
  TwoColumnDictionary
} from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import CmkCode from 'cmk-ui-library/components/CmkCode.vue'
import type { CmkWizardStepProps } from 'cmk-ui-library/components/CmkWizard'
import { CmkWizardButton, CmkWizardStep } from 'cmk-ui-library/components/CmkWizard'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { immediateWatch } from 'cmk-ui-library/lib/watch.ts'
import { type Ref, computed, ref } from 'vue'

import type { ValidationMessages } from '@/form'

import type { OAuth2FormData } from '@/mode-oauth2-connection/lib/service/oauth2-connection-api.ts'

import FormEdit from '../../form/FormEdit.vue'
import {
  buildRedirectUri,
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
    urls: Oauth2Urls
  }
>()
const model = defineModel<{ data: OAuth2FormData; validation: ValidationMessages }>({
  required: true
})
const overrideSite: Ref<string | null> = ref(null)
const redirectUri = computed(() =>
  buildRedirectUri(props.urls.redirect, overrideSite.value, props.urls.site_redirect_urls)
)
const redirectUriValid = computed(() => {
  const url = new URL(redirectUri.value)
  if (url.protocol === 'https:') {
    return true
  }
  return url.protocol === 'http:' && url.hostname === 'localhost'
})

const groupName = 'Redirect URI'
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
    overrideSite.value = newValue.override_site ?? null
    const filteredKeys = new Set(filteredDictionary.value.elements.map((e) => e.name))
    const baseData = Object.fromEntries(
      Object.entries(model.value.data).filter(([key]) => !filteredKeys.has(key))
    ) as OAuth2FormData
    model.value.data = { ...baseData, ...newValue }
  },
  { deep: true }
)
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading type="h2"> {{ _t('Add redirect URI') }}</CmkHeading>
    </template>

    <template #content>
      <FormEdit
        v-model:data="filteredData"
        :backend-validation="filteredValidation"
        :spec="filteredDictionary"
      />
      {{
        _t(
          'Open the Redirect URIs or navigate to the Authentication settings and register the following Web redirect URI'
        )
      }}
      <CmkAlert
        v-if="!redirectUriValid"
        variant="warning"
        :text="
          _t(
            'Only valid redirect URIs starting with https:// or http://localhost can be used. Please check if either of these two options can be applied.'
          )
        "
      />
      <CmkCode
        class="mode-oauth2-connection-redirect-u-r-i__cmk-code"
        :code-text="
          buildRedirectUri(props.urls.redirect, overrideSite, props.urls.site_redirect_urls)
        "
      />
    </template>

    <template #actions>
      <CmkWizardButton type="next" />
      <CmkWizardButton type="previous" />
    </template>
  </CmkWizardStep>
</template>

<style scoped>
.mode-oauth2-connection-redirect-u-r-i__cmk-code {
  line-break: normal;
}
</style>
