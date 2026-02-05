<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { type Oauth2ConnectionConfig } from 'cmk-shared-typing/typescript/mode_oauth2_connection'
import type { FormSpec } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { ref } from 'vue'

import { immediateWatch } from '@/lib/watch.ts'

import CmkWizard from '@/components/CmkWizard'

import type { ValidationMessages } from '@/form'

import type { OAuth2FormData } from '@/mode-oauth2-connection/lib/service/oauth2-connection-api.ts'

import { type Oauth2ConnectionApi } from './lib/service/oauth2-connection-api'
import AddIDs from './steps/AddIDs.vue'
import AppPermissions from './steps/AppPermissions.vue'
import AuthorizeConnection from './steps/AuthorizeConnection.vue'
import ClientSecret from './steps/ClientSecret.vue'
import MicrosoftEntraIDApp from './steps/MicrosoftEntraIDApp.vue'
import RedirectURI from './steps/RedirectURI.vue'
import SaveConnection from './steps/SaveConnection.vue'

const props = defineProps<{
  config: Oauth2ConnectionConfig
  formSpec: {
    id: string
    spec: FormSpec
    validation?: ValidationMessages
    data: OAuth2FormData
  }
  authorityMapping: Record<string, string>
  api: Oauth2ConnectionApi
  connectorType: 'microsoft_entra_id'
}>()

const modelRef = ref<{ data: OAuth2FormData; validation: ValidationMessages }>({
  data: props.formSpec.data,
  validation: props.formSpec.validation ?? []
})

immediateWatch(
  () => props.formSpec.data,
  (newValue) => {
    modelRef.value.data = newValue
  }
)

immediateWatch(
  () => props.formSpec.validation,
  (newValue) => {
    modelRef.value.validation = newValue ?? []
  }
)

const currentStep = ref<number>(1)
</script>

<template>
  <div class="mode-oauth2-connection-create-o-auth2connection">
    <CmkWizard v-model="currentStep" mode="guided">
      <MicrosoftEntraIDApp :index="1" :is-completed="() => currentStep > 1" />
      <AddIDs
        v-model="modelRef"
        :form-spec="formSpec"
        :index="2"
        :is-completed="() => currentStep > 2"
      />
      <RedirectURI :urls="config.urls" :index="3" :is-completed="() => currentStep > 3" />
      <AppPermissions :index="4" :is-completed="() => currentStep > 4" />
      <ClientSecret
        v-model="modelRef"
        :form-spec="formSpec"
        :index="5"
        :is-completed="() => currentStep > 5"
      />
      <AuthorizeConnection :index="6" :is-completed="() => currentStep > 6" />
      <SaveConnection
        v-model="modelRef"
        :urls="config.urls"
        :connector-type="connectorType"
        :api="api"
        :authority-mapping="authorityMapping"
        :ident="formSpec.data.ident"
        :form-spec="formSpec"
        :index="7"
        :is-completed="() => currentStep > 7"
      />
    </CmkWizard>
  </div>
</template>

<style scoped>
.mode-oauth2-connection-create-o-auth2connection {
  max-width: 628px;
}
</style>
