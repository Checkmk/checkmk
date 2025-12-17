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

export interface IAgentTokenGenerationRequest {
  comment: string
  expires_at: string | null
}

export interface IAgentTokenGenerationResponse {
  id: string
  title: string
  domainType: string
}

const { _t } = usei18n()
const props = defineProps<{
  description?: TranslatedString | undefined
  generateComment: string
  hostName: string
  expiresAt?: string | null | undefined
}>()

const ott = defineModel<string | null | Error>({ required: true })
const ottGenerating = ref(false)
const ottGenerated = ref(false)
const ottError = ref<Error | null>(null)
const api = new Api('api/internal/', [['Content-Type', 'application/json']])

async function generateOTT() {
  ottGenerating.value = true

  try {
    const res = (await api.post('domain-types/agent_registration_token/collections/all', {
      comment: props.generateComment,
      host: props.hostName,
      expires_at: props.expiresAt || null
    } as IAgentTokenGenerationRequest)) as IAgentTokenGenerationResponse

    ott.value = res.id
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
      class="mh-generate-registration-token__button"
      @click="generateOTT"
    >
      <CmkIcon name="signature-key" class="mh-generate-registration-token__icon" />
      {{ _t('Generate registration token') }}
    </CmkButton>

    <CmkAlertBox v-else variant="loading">{{ _t('Generating registration token') }}</CmkAlertBox>
  </template>
  <template v-else>
    <CmkAlertBox v-if="ottError" variant="error">{{
      _t(`Error on generating registration token: ${ottError.message}`)
    }}</CmkAlertBox>
    <CmkAlertBox v-else variant="success">{{
      _t('Successfully generated registration token')
    }}</CmkAlertBox>
  </template>
</template>

<style scoped>
.mh-generate-registration-token__button {
  margin: var(--dimension-4) 0 var(--dimension-6);

  .mh-generate-registration-token__icon {
    margin-right: var(--dimension-4);
  }
}
</style>
