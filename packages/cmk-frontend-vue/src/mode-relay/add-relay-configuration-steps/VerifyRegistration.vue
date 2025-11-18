<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { ref, watch } from 'vue'

import usei18n from '@/lib/i18n'
import { getRelayCollection } from '@/lib/rest-api-client/relay/client'

import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'
import { CmkWizardButton, CmkWizardStep } from '@/components/CmkWizard'
import type { CmkWizardStepProps } from '@/components/CmkWizard'
import { getWizardContext } from '@/components/CmkWizard/utils.ts'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

const { _t } = usei18n()

const props = defineProps<CmkWizardStepProps & { relayName: string }>()

defineEmits(['openCreateHostPage', 'openRelayOverviewPage'])

const context = getWizardContext()

const loading = ref(true)
const registrationSuccess = ref(false)
const unexpectedErrorMessage = ref('')

async function verifyRegistration() {
  loading.value = true
  registrationSuccess.value = false
  unexpectedErrorMessage.value = ''

  try {
    const relays = await getRelayCollection()
    registrationSuccess.value = relays.some((relay) => relay.alias === props.relayName)
  } catch (err) {
    unexpectedErrorMessage.value = err instanceof Error ? err.message : 'Unknown error'
  } finally {
    loading.value = false
  }
}

watch(
  () => context.isSelected(props.index),
  (isSelected) => {
    if (isSelected) {
      void verifyRegistration()
    }
  },
  { immediate: true }
)
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading type="h2"> {{ _t('Verify registration') }}</CmkHeading>
    </template>

    <template #content>
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

      <CmkAlertBox v-else-if="registrationSuccess" variant="success">
        {{ _t('Relay registered and saved successfully!') }}
      </CmkAlertBox>
      <CmkAlertBox v-else variant="error">
        <template v-if="unexpectedErrorMessage">
          {{ unexpectedErrorMessage }}
        </template>
        <template v-else>
          {{ _t("Registration failed and Relay couldn't be saved.") }}
        </template>
      </CmkAlertBox>
    </template>

    <template #actions>
      <CmkWizardButton
        v-if="registrationSuccess"
        type="finish"
        :override-label="_t('Continue to add host')"
        @click="$emit('openCreateHostPage')"
      />
      <CmkWizardButton
        v-if="registrationSuccess"
        type="other"
        :override-label="_t('Go to relay overview')"
        icon-name="relay-menu"
        @click="$emit('openRelayOverviewPage')"
      />
      <CmkWizardButton type="previous" />
    </template>
  </CmkWizardStep>
</template>
