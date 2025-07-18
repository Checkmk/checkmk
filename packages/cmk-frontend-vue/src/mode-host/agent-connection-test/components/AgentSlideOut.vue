<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, watch } from 'vue'
import usei18n from '@/lib/i18n'

import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkDialog from '@/components/CmkDialog.vue'
import CmkButton from '@/components/CmkButton.vue'
import CmkTabs from '@/components/CmkTabs/CmkTabs.vue'
import CmkTab from '@/components/CmkTabs/CmkTab.vue'
import CmkTabContent from '@/components/CmkTabs/CmkTabContent.vue'
import ToggleButtonGroup from '@/components/ToggleButtonGroup.vue'
import CmkCode from '@/components/CmkCode.vue'
import type { PackageOptions } from '@/mode-host/agent-connection-test/components/AgentInstallSlideOutContent.vue'

export interface AgentSlideOutTabs {
  id: string
  title: string
  install_msg?: string
  install_cmd?: string
  install_deb_cmd?: string
  install_rpm_cmd?: string
  install_tgz_cmd?: string
  registration_msg?: string
  registration_cmd?: string
  toggle_button_options?: PackageOptions
}

defineProps<{
  dialog_msg: string
  tabs: AgentSlideOutTabs[]
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

const packageFormatRpm = 'rpm'
const packageFormatDeb = 'deb'
const packageFormatTgz = 'tgz'

const model = ref(packageFormatDeb)
watch(model, (newValue) => {
  model.value = newValue
})
</script>

<template>
  <CmkButton
    :title="t('ads-close-and-test', 'Close & test agent connection')"
    class="close_and_test"
    @click="close"
  >
    {{ t('ads-close-and-test', 'Close & test agent connection') }}
  </CmkButton>
  <CmkButton
    :title="t('ads-all-agents', 'View all agents')"
    class="all_agents"
    @click="() => openAllAgentsPage(url)"
  >
    {{ t('ads-all-agents', 'View all agents') }}
  </CmkButton>
  <CmkDialog :message="dialog_msg" :dismissal_button="{ title: 'Do not show again', key: 'key' }" />
  <CmkHeading type="h4" class="heading">
    {{ t('ads-heading2', 'Select the type of system you want to monitor') }}
  </CmkHeading>
  <CmkTabs v-model="openedTab">
    <template #tabs>
      <CmkTab v-for="tab in tabs" :id="tab.id" :key="tab.id" class="tabs">
        <h2>{{ tab.title }}</h2>
      </CmkTab>
    </template>
    <template #tab-contents>
      <CmkTabContent v-for="tab in tabs" :id="tab.id" :key="tab.id">
        <ToggleButtonGroup
          v-if="tab.toggle_button_options"
          v-model="model"
          :options="tab.toggle_button_options"
        />
        <CmkCode
          v-if="tab.install_msg && tab.install_cmd"
          :title="tab.install_msg"
          :code_txt="tab.install_cmd"
        />
        <CmkCode
          v-if="tab.install_msg && tab.install_deb_cmd && model === packageFormatDeb"
          :title="tab.install_msg"
          :code_txt="tab.install_deb_cmd"
        />
        <CmkCode
          v-if="tab.install_msg && tab.install_rpm_cmd && model === packageFormatRpm"
          :title="tab.install_msg"
          :code_txt="tab.install_rpm_cmd"
        />
        <CmkCode
          v-if="tab.install_msg && tab.install_tgz_cmd && model === packageFormatTgz"
          :title="tab.install_msg"
          :code_txt="tab.install_tgz_cmd"
        />
        <CmkCode
          v-if="tab.registration_msg && tab.registration_cmd"
          :title="tab.registration_msg"
          :code_txt="tab.registration_cmd"
        />
        <CmkHeading type="h4">
          {{
            t(
              'agent-download-finish-msg',
              'After installing, you can close the slideout and test the agent connection.'
            )
          }}
        </CmkHeading>
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
</style>
