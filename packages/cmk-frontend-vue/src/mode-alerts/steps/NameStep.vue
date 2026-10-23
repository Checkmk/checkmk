<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import type { CmkWizardStepProps } from 'cmk-ui-library/components/CmkWizard'
import { CmkWizardButton, CmkWizardStep } from 'cmk-ui-library/components/CmkWizard'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import CmkLabelRequired from 'cmk-ui-library/components/user-input/CmkLabelRequired.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import useId from 'cmk-ui-library/lib/useId'
import { computed, ref } from 'vue'

import { type AlertModel, alertName } from '@/mode-alerts/types'

const { _t } = usei18n()

defineProps<CmkWizardStepProps>()

const model = defineModel<AlertModel>({ required: true })

const nameFieldId = useId()
const displayErrors = ref(false)

function getNameErrors(): string[] {
  return alertName(model.value) === '' ? [_t('An alert name is required')] : []
}

const nameErrors = computed(() => (displayErrors.value ? getNameErrors() : []))

function validate(): Promise<boolean> {
  displayErrors.value = true
  return Promise.resolve(getNameErrors().length === 0)
}
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading type="h3">{{ _t('Name the alert') }}</CmkHeading>
    </template>

    <template #content>
      <div class="mode-alerts-name-step">
        <CmkLabel :for="nameFieldId">
          {{ _t('Alert name') }}
          <CmkLabelRequired />
        </CmkLabel>
        <CmkInput
          :id="nameFieldId"
          v-model="model.name"
          type="text"
          field-size="large"
          :external-errors="nameErrors"
        />
      </div>
    </template>

    <template #actions>
      <CmkWizardButton type="next" :validation-cb="validate" />
    </template>
  </CmkWizardStep>
</template>

<style scoped>
.mode-alerts-name-step {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
  max-width: 620px;
}
</style>
