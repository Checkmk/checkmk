<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { CreateRelay } from 'cmk-shared-typing/typescript/create_relay'
import { ref } from 'vue'

import CmkWizard from '@/components/CmkWizard'

import ExecuteInstallationScript from './add-relay-configuration-steps/ExecuteInstallationScript.vue'
import InstallRelay from './add-relay-configuration-steps/InstallRelay.vue'
import NameRelay from './add-relay-configuration-steps/NameRelay.vue'
import VerifyRegistration from './add-relay-configuration-steps/VerifyRegistration.vue'

const props = defineProps<CreateRelay>()

const currentStep = ref<number>(1)
const relayAlias = ref<string>('')
const relayId = ref<string>('')

const openCreateHostPage = () => {
  const url = `${props.urls.create_host}&relay=${relayId.value}&prefill=relay`
  window.location.href = url
}
const openRelayOverviewPage = () => {
  window.location.href = props.urls.relay_overview
}
</script>

<template>
  <div class="mode-relay-mode-create-relay-app">
    <CmkWizard v-model="currentStep" mode="guided">
      <InstallRelay
        :domain="props.domain"
        :site-name="props.site_name"
        :index="1"
        :is-completed="() => currentStep > 1"
      />
      <NameRelay
        v-model="relayAlias"
        :index="2"
        :is-completed="() => currentStep > 2"
        :alias-validation-regex="props.alias_validation.regex"
        :alias-validation-regex-help="props.alias_validation.regex_help"
      />
      <ExecuteInstallationScript
        :relay-alias="relayAlias"
        :site-name="props.site_name"
        :domain="props.domain"
        :site-version="props.site_version"
        :url-to-get-an-automation-secret="props.urls.automation_secret"
        :is-cloud-edition="props.is_cloud_edition"
        :user-id="props.user_id"
        :index="3"
        :is-completed="() => currentStep > 3"
      />
      <VerifyRegistration
        v-model="relayId"
        :relay-alias="relayAlias"
        :index="4"
        :is-completed="() => currentStep > 4"
        @open-create-host-page="openCreateHostPage"
        @open-relay-overview-page="() => openRelayOverviewPage()"
      />
    </CmkWizard>
  </div>
</template>

<style scoped>
.mode-relay-mode-create-relay-app {
  max-width: 628px;
}
</style>
