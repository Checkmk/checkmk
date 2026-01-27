<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { type Oauth2ConnectionConfig } from 'cmk-shared-typing/typescript/mode_oauth2_connection'
import type { FormSpec } from 'cmk-shared-typing/typescript/vue_formspec_components'
import { provide } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import type { ValidationMessages } from '@/form'

import CreateOAuth2Connection from '@/mode-oauth2-connection/CreateOAuth2Connection.vue'
import type { OAuth2FormData } from '@/mode-oauth2-connection/lib/service/oauth2-connection-api.ts'

import { Oauth2ConnectionApi } from './lib/service/oauth2-connection-api'
import { submitKey } from './lib/submitKey'

const { _t } = usei18n()

const props = defineProps<{
  config: Oauth2ConnectionConfig
  form_spec: {
    id: string
    spec: FormSpec
    validation?: ValidationMessages
    data: OAuth2FormData
  }
  authority_mapping: Record<string, string>
  new: boolean
  connector_type: 'microsoft_entra_id'
}>()

const api = new Oauth2ConnectionApi()

async function submit(data: OAuth2FormData): Promise<TranslatedString | null> {
  const res = props.new
    ? await api.saveOAuth2Connection(data, props.connector_type)
    : await api.updateOAuth2Connection(data.ident, data, props.connector_type)
  if (res.type === 'success') {
    window.location.href = props.config.urls.back
    return null
  }
  return _t(`Failed to save OAuth2 connection`)
}

provide(submitKey, submit)
</script>

<template>
  <CreateOAuth2Connection
    :config="config"
    :form-spec="form_spec"
    :authority-mapping="authority_mapping"
    :api="api"
    :connector-type="connector_type"
    @submitted="submit"
  />
</template>
