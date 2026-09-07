<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import CmkTabs, { CmkTab, CmkTabContent } from 'cmk-ui-library/components/CmkTabs'
import CmkToggleButtonGroup from 'cmk-ui-library/components/CmkToggleButtonGroup.vue'
import CmkWizard from 'cmk-ui-library/components/CmkWizard'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { useDismissDialog } from 'cmk-ui-library/lib/useDismissDialog'
import usePersistentRef from 'cmk-ui-library/lib/usePersistentRef'
import { ref, watch } from 'vue'

import type { AgentSlideOutTabs } from '../lib/type_def'
import InstallAgentStep from './steps/InstallAgentStep.vue'
import RegisterAgent from './steps/RegisterAgent.vue'
import SaveHostStep from './steps/SaveHostStep.vue'
import TestConnectionStep from './steps/TestConnectionStep.vue'

const props = defineProps<{
  dialogMsg: TranslatedString
  tabs: AgentSlideOutTabs[]
  allAgentsUrl: string
  userSettingsUrl: string
  closeButtonTitle: TranslatedString
  saveHost: boolean
  hostExists?: boolean
  setupError?: boolean
  agentInstalled: boolean
  isPushMode: boolean
  hostName: string
  siteId: string
  agentReceiverPortIsDefault: boolean
}>()

const { _t } = usei18n()

const emit = defineEmits(['close'])
const close = () => {
  emit('close')
}

const { isShown: alertShown, dismiss: dismissAlert } = useDismissDialog('agent_slideout')

const openedTab = ref<string>(sessionStorage.getItem('slideInTabState') || 'linux')

const openAllAgentsPage = (url: string) => {
  window.open(url, '_blank')
}

const model = ref(sessionStorage.getItem('slideInModelState') || 'deb')
sessionStorage.removeItem('slideInModelState')
sessionStorage.removeItem('slideInTabState')

const selectedVariantId = usePersistentRef<string>('slideInSelectedVariantId', 'powershell', (v) =>
  typeof v === 'string' ? v : 'powershell'
)

// eslint-disable-next-line @typescript-eslint/no-explicit-any
declare const cmk: any
function saveHostAction() {
  sessionStorage.setItem('reopenSlideIn', 'true')
  sessionStorage.setItem('slideInModelState', model.value)
  sessionStorage.setItem('slideInTabState', openedTab.value)
  sessionStorage.setItem('slideInAgentInstalled', String(props.agentInstalled))
  cmk.page_menu.form_submit('edit_host', 'save_and_edit')
}
const ott = ref<string | null | Error>(null)
watch([openedTab, model], () => {
  ott.value = null
})

const currentStep = ref(getInitStep())
function getInitStep() {
  if (props.saveHost) {
    return 1
  }
  if (!props.agentInstalled) {
    return 2
  }
  return 3
}
</script>

<template>
  <CmkButton :title="closeButtonTitle" class="close_and_test" @click="close">
    <CmkIcon name="connection-tests" />
    {{ closeButtonTitle }}
  </CmkButton>
  <CmkButton
    :title="hostExists ? _t('View host agents') : _t('View all agents')"
    class="all_agents"
    @click="() => openAllAgentsPage(allAgentsUrl)"
  >
    <CmkIcon name="frameurl" />
    {{ hostExists ? _t('View host agents') : _t('View all agents') }}
  </CmkButton>
  <CmkAlertBox
    v-if="alertShown"
    :buttons="[
      {
        title: _t('Do not show again'),
        variant: 'optional',
        onclick: dismissAlert
      }
    ]"
  >
    {{ dialogMsg }}
  </CmkAlertBox>
  <CmkHeading type="h4" class="select-heading">
    {{ _t('Select the type of system you want to monitor') }}
  </CmkHeading>
  <CmkTabs v-model="openedTab">
    <template #tabs>
      <CmkTab v-for="tab in tabs" :id="tab.id" :key="tab.id" class="tabs">
        <CmkHeading type="h2">{{ tab.title }}</CmkHeading>
      </CmkTab>
    </template>
    <template #tab-contents>
      <CmkTabContent v-for="tab in tabs" :id="tab.id" :key="tab.id">
        <CmkToggleButtonGroup
          v-if="tab.subTabs && tab.subTabs.length > 1"
          v-model="model"
          :options="tab.subTabs.map((st) => ({ label: st.label, value: st.id }))"
        />
        <CmkWizard v-model="currentStep" mode="guided">
          <SaveHostStep
            :index="1"
            :is-completed="() => currentStep > 1 || !saveHost"
            :is-active="currentStep === 1"
            :host-name="hostName"
            :save-host="saveHost"
            :host-exists="hostExists ?? false"
            :setup-error="setupError ?? false"
            @save-host="saveHostAction"
            @close="close"
          />

          <InstallAgentStep
            v-model:ott="ott"
            v-model:selected-variant-id="selectedVariantId"
            v-model:package-id="model"
            :index="2"
            :is-completed="() => currentStep > 2 || agentInstalled"
            :is-active="currentStep === 2"
            :tab="tab"
            :site-id="siteId"
          />

          <RegisterAgent
            v-model:selected-variant-id="selectedVariantId"
            :index="3"
            :is-completed="() => currentStep > 3 || !tab.registrationMsg"
            :tab="tab"
            :is-push-mode="isPushMode"
            :close-button-title="closeButtonTitle"
            :host-name="hostName"
            :site-id="siteId"
            :user-settings-url="userSettingsUrl"
            :agent-receiver-port-is-default="agentReceiverPortIsDefault"
            @close="close"
          ></RegisterAgent>

          <TestConnectionStep
            v-if="isPushMode"
            v-model:selected-variant-id="selectedVariantId"
            :index="4"
            :is-completed="() => currentStep > 4"
            :is-active="currentStep === 4"
            :tab="tab"
            :close-button-title="closeButtonTitle"
            @close="close"
          />
        </CmkWizard>
      </CmkTabContent>
    </template>
  </CmkTabs>
</template>

<style scoped>
/* stylelint-disable checkmk/vue-bem-naming-convention */
.select-heading {
  margin-top: var(--dimension-5);
  margin-bottom: var(--dimension-4);
}

button.close_and_test {
  gap: var(--dimension-4);
}

button.all_agents {
  gap: var(--dimension-4);
  margin-left: var(--spacing);
}

.tabs {
  display: flex;
  flex-direction: row;
  align-items: center;

  > h2 {
    margin: 0;
    padding: 0;
  }

  > .cmk-icon {
    margin-right: 16px;
  }
}
</style>
