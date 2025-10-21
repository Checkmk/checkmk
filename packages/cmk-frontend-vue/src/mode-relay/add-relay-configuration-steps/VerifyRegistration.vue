<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import usei18n from '@/lib/i18n'
import { getRelayCollection } from '@/lib/rest-api-client/relay/client'

import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

const { _t } = usei18n()

const props = defineProps<{ relayName: string }>()

const loading = ref(true)
const registrationSuccess = ref(false)
const unexpectedErrorMessage = ref('')

onMounted(async () => {
  try {
    const relays = await getRelayCollection()
    registrationSuccess.value = relays.some((relay) => relay.alias === props.relayName)
  } catch (err) {
    unexpectedErrorMessage.value = err instanceof Error ? err.message : 'Unknown error'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <CmkParagraph>
    {{
      _t(
        'After the registration is triggered, verify the registration between the Relay and Checkmk site.'
      )
    }}
  </CmkParagraph>
  <span v-if="loading">
    <CmkIcon name="load-graph" />
    {{ _t('Verifying the registration...') }}
  </span>

  <CmkAlertBox v-if="registrationSuccess && !loading" variant="success">
    {{ _t('Relay registered and saved successfully!') }}
  </CmkAlertBox>
  <CmkAlertBox v-if="!registrationSuccess && !loading" variant="error">
    <template v-if="unexpectedErrorMessage">
      {{ unexpectedErrorMessage }}
    </template>
    <template v-else>
      {{ _t("Registration failed and Relay couldn't be saved.") }}
    </template>
  </CmkAlertBox>
</template>
