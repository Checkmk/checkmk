<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { type Oauth2ConnectionConfig } from 'cmk-shared-typing/typescript/mode_oauth2_connection'
import type { FormSpec } from 'cmk-shared-typing/typescript/vue_formspec_components'

import type { ValidationMessages } from '@/form'

import CreateOAuth2Connection from '@/mode-oauth2-connection/CreateOAuth2Connection.vue'
import type { OAuth2FormData } from '@/mode-oauth2-connection/lib/service/oauth2-connection-api.ts'

defineProps<{
  config: Oauth2ConnectionConfig
  form_spec: {
    id: string
    spec: FormSpec
    validation?: ValidationMessages
    data: OAuth2FormData
  }
  authority_mapping: Record<string, string>
}>()
</script>

<template>
  <CreateOAuth2Connection
    :config="config"
    :form-spec="form_spec"
    :authority-mapping="authority_mapping"
  />
</template>
