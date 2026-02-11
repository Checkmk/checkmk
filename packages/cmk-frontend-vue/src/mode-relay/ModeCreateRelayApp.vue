<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { CreateRelay } from 'cmk-shared-typing/typescript/create_relay'
import { ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkWizard from '@/components/CmkWizard'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import ExecuteInstallationScript from './add-relay-configuration-steps/ExecuteInstallationScript.vue'
import InstallPodman from './add-relay-configuration-steps/InstallPodman.vue'
import InstallRelay from './add-relay-configuration-steps/InstallRelay.vue'
import NameRelay from './add-relay-configuration-steps/NameRelay.vue'
import VerifyRegistration from './add-relay-configuration-steps/VerifyRegistration.vue'

const { _t } = usei18n()

const props = defineProps<CreateRelay>()

const currentStep = ref<number>(1)
const relayAlias = ref<string>('')
const relayId = ref<string>('')

const openCreateHostPage = () => {
  const url = `${props.urls.create_host}&relayid=${relayId.value}&prefill=relay`
  window.location.href = url
}
const openRelayOverviewPage = () => {
  window.location.href = props.urls.relay_overview
}
</script>

<template>
  <div class="mode-relay-mode-create-relay-app">
    <CmkParagraph>
      {{ _t('The Relay is officially supported to run on the following operating systems:') }}
      <ul>
        <li v-for="os in props.supported_os" :key="os">{{ os }}</li>
      </ul>
    </CmkParagraph>
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
      <InstallPodman :index="3" :is-completed="() => currentStep > 3" />
      <ExecuteInstallationScript
        :relay-alias="relayAlias"
        :site-name="props.site_name"
        :domain="props.domain"
        :site-version="props.site_version"
        :url-to-get-an-automation-secret="props.urls.automation_secret"
        :is-cloud-edition="props.is_cloud_edition"
        :user-id="props.user_id"
        :index="4"
        :is-completed="() => currentStep > 4"
      />
      <VerifyRegistration
        v-model="relayId"
        :relay-alias="relayAlias"
        :documentation-url="props.urls.documentation"
        :index="5"
        :is-completed="() => currentStep > 5"
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
