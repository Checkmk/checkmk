<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'
import usei18n from '@/lib/i18n'

import CmkHeading2 from '@/components/typography/CmkHeading2.vue'
import CmkDialog from '@/components/CmkDialog.vue'
import CmkButton from '@/components/CmkButton.vue'
import CmkTabs from '@/components/CmkTabs/CmkTabs.vue'
import CmkTab from '@/components/CmkTabs/CmkTab.vue'
import CmkTabContent from '@/components/CmkTabs/CmkTabContent.vue'
import type { AgentInstallTabs } from '@/mode-host/agent-connection-test/components/AgentInstallSlideOutContent.vue'

defineProps<{
  tabs: AgentInstallTabs[]
  url: string
}>()

const { t } = usei18n('agent_slideout')

const emit = defineEmits(['close'])
const close = () => {
  emit('close')
}

const openedTab = ref<string | number>('linux')

const openAllAgentsPage = (url: string) => {
  window.open(url, '_blank')
}
</script>

<template>
  <CmkButton
    :title="t('ads_close_and_test', 'Close & test agent connection')"
    class="close_and_test"
    @click="close"
  >
    {{ t('ads_close_and_test', 'Close & test agent connection') }}
  </CmkButton>
  <CmkButton
    :title="t('ads_all_agents', 'View all agents')"
    class="all_agents"
    @click="() => openAllAgentsPage(url)"
  >
    {{ t('ads_all_agents', 'View all agents') }}
  </CmkButton>
  <CmkDialog
    :message="
      t(
        'ads_dialog_msg',
        'To monitor systems like Linux or Windows with Checkmk, you need to install an agent on these systems. This agent acts as a small program that collects data about the systems state, such as how much storage is used or the CPU load'
      )
    "
    :dismissal_button="{ title: 'Do not show again', key: 'key' }"
  />
  <CmkHeading2 class="heading">
    {{ t('ads_heading2', 'Select the type of system you want to monitor') }}
  </CmkHeading2>
  <CmkTabs v-model="openedTab">
    <template #tabs>
      <CmkTab v-for="tab in tabs" :id="tab.id" :key="tab.id" class="tabs">
        <h2>{{ tab.title }}</h2>
      </CmkTab>
    </template>
    <template #tab-contents>
      <CmkTabContent v-for="tab in tabs" :id="tab.id" :key="tab.id">
        <p>{{ tab.install_msg }}</p>
        <div class="code_container">
          <code>
            {{ t('ags_placeholder', 'Placeholder for code component') }}
          </code>
        </div>
        <p>{{ tab.registration_msg }}</p>
        <div class="code_container">
          <code>
            {{ t('ags_placeholder', 'Placeholder for code component') }}
          </code>
        </div>
        <p>
          {{
            t(
              'agent_download_finish_msg',
              'After installing, you can close the slideout and test the agent connection.'
            )
          }}
        </p>
      </CmkTabContent>
    </template>
  </CmkTabs>
</template>

<style scoped>
h2.heading {
  margin-top: var(--spacing);
  margin-bottom: var(--spacing);
}

button.all_agents {
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

/*TODO Can be removed if component is implemented*/
.code_container {
  padding: var(--spacing);
  background: var(--grey-4);
  color: #abb2bf;
  border-radius: var(--spacing);
}
</style>
