<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { ref } from 'vue'

import CmkWizard from '@/components/CmkWizard'

import DeployRelay from './add-relay-configuration-steps/DeployRelay.vue'
import NameRelay from './add-relay-configuration-steps/NameRelay.vue'
import RegisterRelay from './add-relay-configuration-steps/RegisterRelay.vue'
import VerifyRegistration from './add-relay-configuration-steps/VerifyRegistration.vue'

const props = defineProps<{ create_host_url: string }>()

const currentStep = ref<number>(1)
const relayName = ref<string>('')
const openCreateHostPage = () => {
  const url = `${props.create_host_url}&relay=${relayName.value}&prefill=relay`
  window.location.href = url
}
</script>

<template>
  <div class="mode-relay-mode-create-relay-app">
    <CmkWizard v-model="currentStep" mode="guided">
      <DeployRelay :index="1" :is-completed="() => currentStep > 1" />
      <NameRelay v-model="relayName" :index="2" :is-completed="() => currentStep > 2" />
      <RegisterRelay :relay-name="relayName" :index="3" :is-completed="() => currentStep > 3" />
      <VerifyRegistration
        :relay-name="relayName"
        :index="4"
        :is-completed="() => currentStep > 4"
        @open-create-host-page="openCreateHostPage"
      />
    </CmkWizard>
  </div>
</template>

<style scoped>
.mode-relay-mode-create-relay-app {
  max-width: 628px;
}
</style>
