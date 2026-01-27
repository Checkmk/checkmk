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
  data: OAuth2FormData
}>()

const authorityMapping = computed(() => {
  return Object.fromEntries(
    props.spec.authority_mapping.map((authority) => [
      authority.authority_id,
      authority.authority_name
    ])
  )
})

const modeCreateOAuth2ConnectionFormSpec = computed(() => {
  return {
    id: 'edit',
    spec: props.spec.form_spec,
    validation: props.backendValidation,
    data: props.data
  }
})
const api = new Oauth2ConnectionApi()
</script>

<template>
  <CreateOAuth2Connection
    :config="spec.config"
    :form-spec="modeCreateOAuth2ConnectionFormSpec"
    :authority-mapping="authorityMapping"
    :api="api"
    :connector-type="spec.connector_type"
  />
</template>
