<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'

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

const { _t, _tn } = usei18n()
const props = defineProps<{
  description?: TranslatedString | undefined
  tokenGenerationEndpointUri: string
  tokenGenerationBody: IAgentTokenGenerationRequestBody
  expiresInSeconds?: number | undefined
  showValidityText?: boolean | undefined
}>()

const ott = defineModel<string | null | Error>({ required: true })
const ottGenerating = ref(false)
const ottGenerated = ref(false)
const ottError = ref<Error | null>(null)
const ottExpiry = ref<Date | null>(null)
const noOTT = ref(false)
const api = new Api('api/internal/', [['Content-Type', 'application/json']])
const tokenGenerationBody = ref<IAgentTokenGenerationRequestBody>(props.tokenGenerationBody)

const validityText = computed<TranslatedString | null>(() => {
  const s = props.expiresInSeconds
  if (!s) {
    return null
  }
  let n: number, unit: TranslatedString
  if (s < 60) {
    n = s
    unit = _tn('%{n} second', '%{n} seconds', n, { n })
  } else if (s < 3600) {
    n = Math.round(s / 60)
    unit = _tn('%{n} minute', '%{n} minutes', n, { n })
  } else if (s < 86400) {
    n = Math.round(s / 3600)
    unit = _tn('%{n} hour', '%{n} hours', n, { n })
  } else {
    n = Math.round(s / 86400)
    unit = _tn('%{n} day', '%{n} days', n, { n })
  }
  return _t('This token remains valid for %{duration}.', { duration: unit }) as TranslatedString
})

async function generateOTT() {
  noOTT.value = false
  ottGenerating.value = true

  if (props.expiresInSeconds) {
    const ottExpiryDate = new Date()
    ottExpiryDate.setSeconds(ottExpiryDate.getSeconds() + props.expiresInSeconds)
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
      {{ _t('Generate one-time token') }}
    </CmkButton>

    <CmkAlertBox v-else variant="loading">{{ _t('Generating one-time token') }}</CmkAlertBox>
  </template>
  <template v-else>
    <CmkAlertBox v-if="ottError" variant="error">{{
      _t(`Error generating one-time token: ${ottError.message}`)
    }}</CmkAlertBox>
    <template v-else>
      <CmkAlertBox variant="success">
        <template v-if="showValidityText && validityText">{{ validityText }}</template>
        <template v-else>
          {{ _t('Successfully generated one-time token') }}
          {{ _t(`(Expires: ${ottExpiry?.toLocaleString() || 'never'})`) }}
        </template>
      </CmkAlertBox>
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
