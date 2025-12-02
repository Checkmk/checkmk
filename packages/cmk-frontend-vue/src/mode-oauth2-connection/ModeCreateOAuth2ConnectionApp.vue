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

import AuthorizeApplication from './steps/AuthorizeApplication.vue'
import DefineParams from './steps/DefineParams.vue'

const props = defineProps<{
  config: Oauth2ConnectionConfig
  form_spec: {
    id: string
    spec: FormSpec
    validation?: ValidationMessages
    data: OAuth2FormData
  }
  authority_mapping: Record<string, string>
}>()

const dataRef = ref()
immediateWatch(
  () => props.form_spec.data,
  (newValue) => {
    dataRef.value = newValue
  }
)

const oAuth2Type = 'ms_graph_api' // currently only MS Graph API is supported

const currentStep = ref<number>(1)
</script>

<template>
  <div class="mode-oauth2-connection-mode-create-o-auth2connection-app">
    <CmkWizard v-model="currentStep" mode="guided">
      <DefineParams
        v-model="dataRef"
        :urls="config.urls"
        :form_spec="form_spec"
        :index="1"
        :is-completed="() => currentStep > 1"
      />
      <AuthorizeApplication
        v-model="dataRef"
        :o-auth2-type="oAuth2Type"
        :urls="config.urls"
        :authority-mapping="authority_mapping"
        :index="2"
        :is-completed="() => currentStep > 2"
      />
    </CmkWizard>
  </div>
</template>

<style scoped>
.mode-oauth2-connection-mode-create-o-auth2connection-app {
  max-width: 628px;
}
</style>
