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

export interface IAgentTokenGenerationResponseExtensions {
  comment: string
  issued_at: Date
  expires_at: Date | null
  host_name: string
}

export interface IAgentTokenGenerationResponse {
  id: string
  title: string
  domainType: string
  extensions: IAgentTokenGenerationResponseExtensions
}

export interface IAgentTokenGenerationRequestBody {
  host?: string
  comment?: string
  expires_at?: Date | undefined
}

const { _t } = usei18n()
const props = defineProps<{
  description?: TranslatedString | undefined
  tokenGenerationEndpointUri: string
  tokenGenerationBody: IAgentTokenGenerationRequestBody
  expiresInDays?: number | undefined
}>()

const ott = defineModel<string | null | Error>({ required: true })
const ottGenerating = ref(false)
const ottGenerated = ref(false)
const ottError = ref<Error | null>(null)
const ottExpiry = ref<Date | null>(null)
const noOTT = ref(false)
const api = new Api('api/internal/', [['Content-Type', 'application/json']])
const tokenGenerationBody = ref<IAgentTokenGenerationRequestBody>(props.tokenGenerationBody)

async function generateOTT() {
  noOTT.value = false
  ottGenerating.value = true

  if (props.expiresInDays) {
    const ottExpiryDate = new Date()
    ottExpiryDate.setDate(ottExpiryDate.getDate() + props.expiresInDays)
    tokenGenerationBody.value.expires_at = ottExpiryDate
  }

  try {
    const res = (await api.post(
      props.tokenGenerationEndpointUri,
      props.tokenGenerationBody
    )) as IAgentTokenGenerationResponse

    ott.value = res.id

    ottExpiry.value = null
    if (res.extensions.expires_at) {
      ottExpiry.value = new Date(res.extensions.expires_at)
    }
  } catch (e) {
    ott.value = ottError.value = e as Error
  } finally {
    ottGenerating.value = false
    ottGenerated.value = true
  }
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
</style>
