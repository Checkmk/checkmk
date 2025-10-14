<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkWizard from '@/components/CmkWizard/CmkWizard.vue'
import CmkWizardButton from '@/components/CmkWizard/CmkWizardButton.vue'
import CmkWizardStep from '@/components/CmkWizard/CmkWizardStep.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

import ConnectionCheck from './add-relay-configuration-steps/ConnectionCheck.vue'
import DeployRelay from './add-relay-configuration-steps/DeployRelay.vue'
import RegisterRelay from './add-relay-configuration-steps/RegisterRelay.vue'

const { _t } = usei18n()

const currentStep = ref<number>(1)
</script>

<template>
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
        <CmkHeading type="h2">
          {{ _t('Name the relay and register with your Checkmk site') }}</CmkHeading
        >
      </template>

      <template #content>
        <RegisterRelay></RegisterRelay>
      </template>
      <template #actions>
        <CmkWizardButton type="next" />
      </template>
    </CmkWizardStep>

    <CmkWizardStep :index="3" :is-completed="() => currentStep > 3">
      <template #header>
        <CmkHeading type="h2"> {{ _t('Connection check') }}</CmkHeading>
      </template>

      <template #content>
        <ConnectionCheck></ConnectionCheck>
      </template>
      <template #actions>
        <CmkWizardButton type="finish" />
      </template>
    </CmkWizardStep>
  </CmkWizard>
</template>
