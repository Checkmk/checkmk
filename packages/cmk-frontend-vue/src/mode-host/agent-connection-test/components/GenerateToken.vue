<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import { Api } from '@/lib/api-client'
import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkButton from '@/components/CmkButton.vue'
import CmkIcon from '@/components/CmkIcon'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

export interface IAgentTokenGenerationResponsExtensions {
  comment: string
  issued_at: Date
  expires_at: Date | null
  host_name: string
}

export interface IAgentTokenGenerationResponse {
  id: string
  title: string
  domainType: string
  extensions: IAgentTokenGenerationResponsExtensions
}

const { _t } = usei18n()
const props = defineProps<{
  description?: TranslatedString | undefined
  tokenGenerationEndpointUri: string
  tokenGenerationBody: unknown
}>()

const ott = defineModel<string | null | Error>({ required: true })
const ottGenerating = ref(false)
const ottGenerated = ref(false)
const ottError = ref<Error | null>(null)
const ottExpiry = ref<Date | null>(null)
const noOTT = ref(false)
const api = new Api('api/internal/', [['Content-Type', 'application/json']])

async function generateOTT() {
  noOTT.value = false
  ottGenerating.value = true

  try {
    const res = (await api.post(
      props.tokenGenerationEndpointUri,
      props.tokenGenerationBody
    )) as IAgentTokenGenerationResponse

    ott.value = res.id

    ottExpiry.value = res.extensions.expires_at
  } catch (e) {
    ott.value = ottError.value = e as Error
  } finally {
    ottGenerating.value = false
    ottGenerated.value = true
  }
}

function registerWithUser() {
  noOTT.value = true
  ottGenerated.value = false
  ott.value = new Error('Register agent with user')
}
</script>

<template>
  <template v-if="!ottGenerated">
    <CmkParagraph v-if="description">{{ description }}</CmkParagraph>

    <CmkButton
      v-if="!ottGenerating"
      variant="secondary"
      class="mh-generate-token__button"
      @click="generateOTT"
    >
      <CmkIcon name="signature-key" class="mh-generate-token__icon" />
      {{ _t('Generate token') }}
    </CmkButton>

    <CmkAlertBox v-else variant="loading">{{ _t('Generating token') }}</CmkAlertBox>

    <CmkAlertBox v-if="noOTT">{{
      _t('Regenerate a token to use token authentication.')
    }}</CmkAlertBox>
  </template>
  <template v-else>
    <CmkAlertBox v-if="ottError" variant="error">{{
      _t(`Error on generating token: ${ottError.message}`)
    }}</CmkAlertBox>
    <template v-else>
      <CmkAlertBox variant="success">
        {{ _t('Successfully generated token') }}
        {{ _t(`(Expires: ${ottExpiry?.toLocaleString() || 'never'})`) }}</CmkAlertBox
      >
      <CmkAlertBox>
        {{ _t('If an error occurs during OTT authentication, try to authenticate with a user.') }}
        <br />
        <CmkButton size="small" class="mh-generate-token__auth-with-user" @click="registerWithUser">
          <CmkIcon name="main-user-active" class="mh-generate-token__auth-with-user-icon" />
          {{ _t('Authenticate with user') }}</CmkButton
        ></CmkAlertBox
      >
    </template>
  </template>
</template>

<style scoped>
.mh-generate-token__button {
  margin: var(--dimension-4) 0 var(--dimension-6);

  .mh-generate-token__icon {
    margin-right: var(--dimension-4);
  }
}

.mh-generate-token__auth-with-user {
  margin-top: var(--dimension-4);

  .mh-generate-token__auth-with-user-icon {
    margin-right: var(--dimension-4);
  }
}
</style>
