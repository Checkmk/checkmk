<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import CmkWizard, { CmkWizardButton, CmkWizardStep } from 'cmk-ui-library/components/CmkWizard'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { ref } from 'vue'

import { createAlert } from '@/mode-alerts/alert-client'
import NameAndServicesStep from '@/mode-alerts/steps/NameAndServicesStep.vue'
import { type AlertModel, emptyAlert } from '@/mode-alerts/types'

const { _t } = usei18n()

const currentStep = ref(1)
const model = ref<AlertModel>(emptyAlert())
const saving = ref(false)
const created = ref(false)
const saveError = ref<string | null>(null)

async function saveAlert(): Promise<void> {
  saveError.value = null
  saving.value = true
  try {
    const result = await createAlert(model.value)
    if (result.ok) {
      created.value = true
    } else {
      saveError.value = result.error
    }
  } catch {
    saveError.value = _t('Failed to create the alert.')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="mode-alerts-alert-wizard-app">
    <CmkWizard v-model="currentStep" mode="guided">
      <NameAndServicesStep v-model="model" :index="1" :is-completed="() => currentStep > 1" />

      <CmkWizardStep :index="2" :is-completed="() => false">
        <template #header>
          <CmkHeading type="h3">{{ _t('Define threshold') }}</CmkHeading>
        </template>
        <template #content>
          <CmkParagraph>
            {{ _t('Defining the threshold will become available here.') }}
          </CmkParagraph>
          <CmkAlert v-if="created" variant="success" :text="_t('The alert was created.')" />
          <CmkAlert v-if="saveError" variant="error" :text="untranslated(saveError)" />
        </template>
        <template #actions>
          <CmkWizardButton
            type="finish"
            :override-label="_t('Create alert')"
            :disabled="saving || created"
            @click="saveAlert"
          />
          <CmkWizardButton type="previous" />
        </template>
      </CmkWizardStep>
    </CmkWizard>
  </div>
</template>

<style scoped>
.mode-alerts-alert-wizard-app {
  padding: var(--dimension-6);
  max-width: 900px;
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}
</style>
