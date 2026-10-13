<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import type { CmkWizardStepProps } from 'cmk-ui-library/components/CmkWizard'
import { CmkWizardButton, CmkWizardStep } from 'cmk-ui-library/components/CmkWizard'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import CmkInput from 'cmk-ui-library/components/user-input/CmkInput.vue'
import CmkLabelRequired from 'cmk-ui-library/components/user-input/CmkLabelRequired.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import useId from 'cmk-ui-library/lib/useId'
import { computed, ref } from 'vue'

import { type Relay, getRelayCollection } from '@/mode-relay/relay-client'

const { _t } = usei18n()

const relayAliasId = useId()

defineProps<CmkWizardStepProps>()

const RELAY_ALIAS_REGEX = /^[a-zA-Z0-9_-]+$/

const relayAlias = defineModel<string>({ default: '' })
const savedRelays = ref<Relay[]>([])

const displayErrors = ref(false)

const getAliasErrors = () => {
  const errors: string[] = []
  const alias = relayAlias.value.trim()
  if (alias.length === 0) {
    errors.push(_t('A relay alias is required'))
  } else if (!RELAY_ALIAS_REGEX.test(alias)) {
    errors.push(_t('Allowed characters are letters, digits, underscores, and hyphens.'))
  }
  return errors
}

const getAliasWarnings = () => {
  const warnings: string[] = []
  const alias = relayAlias.value.trim()
  if (alias.length > 0 && savedRelays.value.some((relay) => relay.alias === alias)) {
    warnings.push(_t('This relay alias is already in use'))
  }
  return warnings
}

const aliasErrors = computed(() => {
  return displayErrors.value ? getAliasErrors() : []
})

const aliasWarnings = computed(() => {
  return displayErrors.value ? getAliasWarnings() : []
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
        <CmkLabel :for="relayAliasId">
          {{ _t('Relay alias') }}
          <CmkLabelRequired />
        </CmkLabel>
        <CmkInput
          :id="relayAliasId"
          v-model="relayAlias"
          type="text"
          field-size="medium"
          :external-errors="aliasErrors"
        />
      </div>
      <CmkAlert
        v-for="warning in aliasWarnings"
        :key="warning"
        variant="warning"
        :text="untranslated(warning)"
      />
      <CmkAlert
        variant="info"
        :text="
          _t(
            'This alias will be used to identify your Relay. It will automatically be inserted into the command shown in the next steps.'
          )
        "
      />
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
