<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed, ref } from 'vue'

import usei18n from '@/lib/i18n'
import { type Relay, getRelayCollection } from '@/lib/rest-api-client/relay/client'

import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkLabel from '@/components/CmkLabel.vue'
import type { CmkWizardStepProps } from '@/components/CmkWizard'
import { CmkWizardButton, CmkWizardStep } from '@/components/CmkWizard'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'
import CmkLabelRequired from '@/components/user-input/CmkLabelRequired.vue'

const { _t } = usei18n()

const props = defineProps<
  CmkWizardStepProps & { aliasValidationRegex: string; aliasValidationRegexHelp: string }
>()

const relayAlias = defineModel<string>({ default: '' })
const savedRelays = ref<Relay[]>([])

const displayErrors = ref(false)

const getAliasErrors = () => {
  const errors: string[] = []
  const alias = relayAlias.value.trim()
  if (alias.length === 0) {
    errors.push('A relay alias is required')
  } else if (savedRelays.value.some((relay) => relay.alias === alias)) {
    errors.push('This relay alias is already in use')
  } else if (!new RegExp(props.aliasValidationRegex).test(alias)) {
    errors.push(props.aliasValidationRegexHelp)
  }
  return errors
}

const aliasErrors = computed(() => {
  return displayErrors.value ? getAliasErrors() : []
})

async function validate(): Promise<boolean> {
  displayErrors.value = true
  savedRelays.value = await getRelayCollection()
  return getAliasErrors().length === 0
}
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading type="h2"> {{ _t('Name the relay') }}</CmkHeading>
    </template>

    <template #content>
      <CmkParagraph>
        {{ _t('Provide a display alias for your Relay. This alias can be changed later.') }}
      </CmkParagraph>
      <div class="mode-relay-name-relay__form-row">
        <CmkLabel>
          {{ _t('Relay alias') }}
          <CmkLabelRequired />
        </CmkLabel>
        <CmkInput
          v-model="relayAlias"
          type="text"
          field-size="MEDIUM"
          :external-errors="aliasErrors"
        />
      </div>
      <CmkAlertBox variant="info">
        {{
          _t(
            'This alias will be used to identify your Relay. It will automatically be inserted into the command shown in the next step.'
          )
        }}
      </CmkAlertBox>
    </template>

    <template #actions>
      <CmkWizardButton type="next" :validation-cb="validate" />
      <CmkWizardButton type="previous" />
    </template>
  </CmkWizardStep>
</template>

<style scoped>
.mode-relay-name-relay__form-row {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: var(--dimension-6);
}
</style>
