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
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { useDismissDialog } from 'cmk-ui-library/lib/useDismissDialog'
import usePersistentRef from 'cmk-ui-library/lib/usePersistentRef'
import { ref } from 'vue'

import { rememberBeforeSaveHost, takeRestoredState } from '../lib/slideoutSession'
import type { AgentSlideOutTabs } from '../lib/type_def'
import AgentFlavourWizard from './AgentFlavourWizard.vue'

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

const restored = takeRestoredState()
const openedTab = ref<string>(restored.tabId ?? 'linux')

const openAllAgentsPage = (url: string) => {
  window.open(url, '_blank')
}

/**
 * Which shell the user prefers is a setting, not progress, so it is shared
 * across flavours and outlives the session. Step progress and the one-time
 * tokens belong to a single flavour and live in `AgentFlavourWizard`.
 */
const shellId = usePersistentRef<string>('slideInSelectedVariantId', 'powershell', (v) =>
  typeof v === 'string' ? v : 'powershell'
)

// eslint-disable-next-line @typescript-eslint/no-explicit-any
declare const cmk: any
function saveHostAction(packageId: string) {
  rememberBeforeSaveHost({
    tabId: openedTab.value,
    packageId,
    agentInstalled: props.agentInstalled
  })
  cmk.page_menu.form_submit('edit_host', 'save_and_edit')
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
  <!-- Hidden panels stay alive so that switching flavours to compare them does
       not throw away wizard progress or a freshly generated one-time token. -->
  <CmkTabs v-model="openedTab" :unmount-on-hide="false">
    <template #tabs>
      <CmkTab v-for="tab in tabs" :id="tab.id" :key="tab.id" class="tabs">
        <CmkHeading type="h2">{{ tab.title }}</CmkHeading>
      </CmkTab>
    </template>
    <template #tab-contents>
      <CmkTabContent v-for="tab in tabs" :id="tab.id" :key="tab.id">
        <AgentFlavourWizard
          v-model:shell-id="shellId"
          :tab="tab"
          :save-host="saveHost"
          :host-exists="hostExists ?? false"
          :setup-error="setupError ?? false"
          :agent-installed="agentInstalled"
          :is-push-mode="isPushMode"
          :host-name="hostName"
          :site-id="siteId"
          :user-settings-url="userSettingsUrl"
          :close-button-title="closeButtonTitle"
          :agent-receiver-port-is-default="agentReceiverPortIsDefault"
          :restored-package-id="
            tab.id === restored.tabId ? (restored.packageId ?? undefined) : undefined
          "
          @save-host="saveHostAction"
          @close="close"
        />
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
