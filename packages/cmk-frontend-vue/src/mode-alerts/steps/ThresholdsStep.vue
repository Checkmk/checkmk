<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { FormSpec } from 'cmk-shared-typing/typescript/vue_formspec_components'
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import type { CmkWizardStepProps } from 'cmk-ui-library/components/CmkWizard'
import { CmkWizardButton, CmkWizardStep } from 'cmk-ui-library/components/CmkWizard'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

import { FormEdit } from '@/form'

import { type AlertModel, hasCompleteThresholds, hasThresholds } from '@/mode-alerts/types'

const { _t } = usei18n()

defineProps<
  CmkWizardStepProps & {
    thresholdsSpec: FormSpec
    saving: boolean
    created: boolean
    saveError: string | null
  }
>()

const emit = defineEmits<{ create: [] }>()

const model = defineModel<AlertModel>({ required: true })

const problem = computed<TranslatedString | null>(() => {
  if (!hasThresholds(model.value)) {
    return _t('Define at least one threshold: upper levels, lower levels or both.')
  }
  if (!hasCompleteThresholds(model.value)) {
    return _t('Fill in the warning and critical levels.')
  }
  return null
})
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading type="h3">{{ _t('Define threshold') }}</CmkHeading>
    </template>

    <template #content>
      <div class="mode-alerts-thresholds-step">
        <CmkParagraph>
          {{ _t('Set the default levels of the selected custom services.') }}
        </CmkParagraph>
        <FormEdit v-model:data="model.thresholds" :spec="thresholdsSpec" :backend-validation="[]" />
        <CmkAlert v-if="problem" variant="info" size="small" :text="problem" />
        <CmkAlert v-if="created" variant="success" :text="_t('The alert was created.')" />
        <CmkAlert v-if="saveError" variant="error" :text="untranslated(saveError)" />
      </div>
    </template>

    <template #actions>
      <CmkWizardButton
        type="finish"
        :override-label="_t('Create alert')"
        :disabled="saving || created || problem !== null"
        @click="emit('create')"
      />
      <CmkWizardButton type="previous" />
    </template>
  </CmkWizardStep>
</template>

<style scoped>
.mode-alerts-thresholds-step {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-5);
  max-width: 620px;
}
</style>
