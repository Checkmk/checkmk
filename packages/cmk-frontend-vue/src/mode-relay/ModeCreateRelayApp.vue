<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkWizard, { CmkWizardButton, CmkWizardStep } from '@/components/CmkWizard'
import CmkHeading from '@/components/typography/CmkHeading.vue'

import DeployRelay from './add-relay-configuration-steps/DeployRelay.vue'
import NameRelay from './add-relay-configuration-steps/NameRelay.vue'
import RegisterRelay from './add-relay-configuration-steps/RegisterRelay.vue'
import VerifyRegistration from './add-relay-configuration-steps/VerifyRegistration.vue'

const { _t } = usei18n()

const currentStep = ref<number>(1)
const relayName = ref<string>('')
</script>

<template>
  <div class="mode-relay-mode-create-relay-app">
    <CmkWizard v-model="currentStep" mode="guided">
      <CmkWizardStep :index="1" :is-completed="() => currentStep > 1">
        <template #header>
          <CmkHeading type="h2"> {{ _t('Deploy the relay to your environment') }}</CmkHeading>
        </template>

        <template #content>
          <DeployRelay></DeployRelay>
        </template>

        <template #actions>
          <CmkWizardButton type="next" />
        </template>
      </CmkWizardStep>

      <CmkWizardStep
        :index="2"
        :is-completed="
          () => {
            return currentStep > 2
          }
        "
      >
        <template #header>
          <CmkHeading type="h2"> {{ _t('Name the relay') }}</CmkHeading>
        </template>

        <template #content>
          <NameRelay v-model="relayName" />
        </template>
        <template #actions>
          <CmkWizardButton type="next" />
          <CmkWizardButton type="previous" />
        </template>
      </CmkWizardStep>

      <CmkWizardStep
        :index="3"
        :is-completed="
          () => {
            return currentStep > 3
          }
        "
      >
        <template #header>
          <CmkHeading type="h2"> {{ _t('Register the relay with your Checkmk site') }}</CmkHeading>
        </template>

        <template #content>
          <RegisterRelay :relay-name="relayName" />
        </template>
        <template #actions>
          <CmkWizardButton type="next" />
          <CmkWizardButton type="previous" />
        </template>
      </CmkWizardStep>

      <CmkWizardStep :index="4" :is-completed="() => currentStep > 4">
        <template #header>
          <CmkHeading type="h2"> {{ _t('Verify registration') }}</CmkHeading>
        </template>

        <template #content>
          <VerifyRegistration :relay-name="relayName"></VerifyRegistration>
        </template>
        <template #actions>
          <CmkWizardButton type="finish" />
          <CmkWizardButton type="previous" />
        </template>
      </CmkWizardStep>
    </CmkWizard>
  </div>
</template>

<style scoped>
.mode-relay-mode-create-relay-app {
  max-width: 628px;
}
</style>
