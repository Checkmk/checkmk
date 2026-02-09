<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type * as FormSpec from 'cmk-shared-typing/typescript/vue_formspec_components'
import { computed } from 'vue'

import { type ValidationMessages } from '@/form/private/validation'

import CreateOAuth2Connection from '@/mode-oauth2-connection/CreateOAuth2Connection.vue'
import { Oauth2ConnectionApi } from '@/mode-oauth2-connection/lib/service/oauth2-connection-api'
import type { OAuth2FormData } from '@/mode-oauth2-connection/lib/service/oauth2-connection-api.ts'

const props = defineProps<{
  spec: FormSpec.Oauth2ConnectionSetup
  backendValidation: ValidationMessages
}>()

const data = defineModel<OAuth2FormData>('data', { required: true })

const authorityMapping = computed(() => {
  return Object.fromEntries(
    props.spec.authority_mapping.map((authority) => [
      authority.authority_id,
      authority.authority_name
    ])
  )
})

// Capture the initial data value so the computed does not depend on data.value.
// The actual data flows through the v-model:data binding on CreateOAuth2Connection,
// not through the formSpec prop. Including data.value here would cause the computed
// to recalculate on every keystroke, which triggers a cascade that overwrites user
// input with replacement_value from existing validation messages.
const initialData = data.value
const modeCreateOAuth2ConnectionFormSpec = computed(() => {
  return {
    id: 'edit',
    spec: props.spec.form_spec,
    validation: props.backendValidation,
    data: initialData
  }
})
const api = new Oauth2ConnectionApi()
</script>

<template>
  <CreateOAuth2Connection
    v-model:data="data"
    :config="spec.config"
    :form-spec="modeCreateOAuth2ConnectionFormSpec"
    :authority-mapping="authorityMapping"
    :api="api"
    :connector-type="spec.connector_type"
  />
</template>
