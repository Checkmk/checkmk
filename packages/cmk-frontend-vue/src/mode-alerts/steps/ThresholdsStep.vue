<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import type { CmkWizardStepProps } from 'cmk-ui-library/components/CmkWizard'
import { CmkWizardButton, CmkWizardStep } from 'cmk-ui-library/components/CmkWizard'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'

const { _t } = usei18n()

defineProps<
  CmkWizardStepProps & {
    saving: boolean
    created: boolean
    saveError: string | null
  }
>()

const emit = defineEmits<{ create: [] }>()
</script>

<template>
  <CmkWizardStep :index="index" :is-completed="isCompleted">
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
        @click="emit('create')"
      />
      <CmkWizardButton type="previous" />
    </template>
  </CmkWizardStep>
</template>
