<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import { CmkWizardButton } from 'cmk-ui-library/components/CmkWizard'
import CmkWizardStep from 'cmk-ui-library/components/CmkWizard/CmkWizardStep.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

defineProps<{
  index: number
  isCompleted: () => boolean
  isActive: boolean
  hostName: string
  saveHost: boolean
  hostExists: boolean
  setupError: boolean
}>()

const emit = defineEmits<{ close: []; saveHost: [] }>()

const { _t } = usei18n()
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
    <template #header>
      <CmkHeading> {{ _t('Save host') }}</CmkHeading>
    </template>

    <template #content>
      <div class="save_host__div">
        <CmkParagraph>
          {{
            _t(
              'Agent registration is only possible for hosts that already exist in Checkmk (they don’t need to be activated yet).'
            )
          }}
        </CmkParagraph>
      </div>
      <div v-if="setupError" class="save_host__div">
        <CmkParagraph class="agent_slideout__paragraph_host_exists">
          <CmkIcon name="cross" />
          {{ _t(`Could not save host "${hostName}". Close the slideout and review your input.`) }}
        </CmkParagraph>
      </div>
      <div v-else-if="!saveHost && hostExists" class="save_host__div">
        <CmkParagraph class="agent_slideout__paragraph_host_exists">
          <CmkIcon name="checkmark" />
          {{ _t(`Host "${hostName}" exists`) }}
        </CmkParagraph>
      </div>
    </template>
    <template #actions>
      <CmkButton v-if="setupError" :title="_t('Close and revise form')" @click="emit('close')">
        <CmkIcon name="edit" />
        {{ _t('Close & review') }}
      </CmkButton>
      <CmkWizardButton
        v-if="saveHost && !setupError"
        :override-label="_t('Save host & next step')"
        type="next"
        @click="emit('saveHost')"
      />
      <CmkWizardButton v-else-if="isActive && !setupError" type="next" />
    </template>
  </CmkWizardStep>
</template>

<style scoped>
/* stylelint-disable checkmk/vue-bem-naming-convention */
.save_host__div {
  margin-bottom: var(--spacing);
}

.agent_slideout__paragraph_host_exists {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
}
</style>
