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
import type { PackageOptions } from '@/mode-host/agent-connection-test/components/AgentSlideOutContent.vue'
import CmkIcon from '@/components/CmkIcon.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'
import CmkLinkCard from '@/components/CmkLinkCard.vue'
import CmkWizard from '@/components/CmkWizard/CmkWizard.vue'
import CmkWizardStep from '@/components/CmkWizard/CmkWizardStep.vue'
import CmkWizardButton from '@/components/CmkWizard/CmkWizardButton.vue'

export interface AgentSlideOutTabs {
  id: string
  title: string
  installMsg?: string
  installCmd?: string | undefined
  installDebCmd?: string
  installRpmCmd?: string
  installTgzCmd?: string | undefined
  registrationMsg?: string
  registrationCmd?: string
  installUrl?: InstallUrl | undefined
  toggleButtonOptions?: PackageOptions
}

export interface InstallUrl {
  title: string
  url: string
  msg: string
  icon?: string
}

const props = defineProps<{
  dialogMsg: string
  tabs: AgentSlideOutTabs[]
  allAgentsUrl: string
  closeButtonTitle: string
  saveHost: boolean
  agentInstalled: boolean
  isPushMode: boolean
  hostName: string
}>()

const { _t } = usei18n()

const emit = defineEmits(['close'])
const close = () => {
  emit('close')
}

const openedTab = ref<string>(sessionStorage.getItem('slideInTabState') || 'linux')

const openAllAgentsPage = (url: string) => {
  window.open(url, '_blank')
}

const packageFormatRpm = 'rpm'
const packageFormatDeb = 'deb'
const packageFormatTgz = 'tgz'

const model = ref(sessionStorage.getItem('slideInModelState') || packageFormatDeb)
watch(model, (newValue) => {
  model.value = newValue
})
sessionStorage.removeItem('slideInModelState')
sessionStorage.removeItem('slideInTabState')

// eslint-disable-next-line @typescript-eslint/no-explicit-any
declare const cmk: any
function saveHostAction() {
  sessionStorage.setItem('reopenSlideIn', 'true')
  sessionStorage.setItem('slideInModelState', model.value)
  sessionStorage.setItem('slideInTabState', openedTab.value)
  cmk.page_menu.form_submit('edit_host', 'save_and_edit')
}
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
    <CmkIcon name="connection_tests" />
    {{ closeButtonTitle }}
  </CmkButton>
  <CmkButton
    :title="_t('View all agents')"
    class="all_agents"
    @click="() => openAllAgentsPage(allAgentsUrl)"
  >
    <CmkIcon name="frameurl" />
    {{ _t('View all agents') }}
  </CmkButton>
  <CmkDialog :message="dialogMsg" :dismissal_button="{ title: 'Do not show again', key: 'key' }" />
  <CmkHeading type="h4" class="select-heading">
    {{ _t('Select the type of system you want to monitor') }}
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
          v-if="tab.toggleButtonOptions"
          v-model="model"
          :options="tab.toggleButtonOptions"
        />
        <CmkWizard v-model="currentStep" mode="guided">
          <CmkWizardStep :index="1" :is-completed="() => currentStep > 1 || !saveHost">
            <template #header>
              <CmkHeading> {{ _t('Save host') }}</CmkHeading>
            </template>

            <template #content>
              <div class="save_host__div">
                <CmkParagraph>
                  {{
                    _t(
                      'Agent registration is only possible for hosts that already exist in Checkmk (they don’t need to be activated yet).'
                    )
                  }}
                </CmkParagraph>
              </div>
              <div v-if="!saveHost" class="save_host__div">
                <CmkParagraph class="agent_slideout__paragraph_host_exists">
                  <CmkIcon name="checkmark" />
                  {{ _t(`Host "${hostName}" exists`) }}
                </CmkParagraph>
              </div>
            </template>
            <template #actions>
              <CmkWizardButton
                v-if="saveHost"
                :override-label="_t('Save host & next step')"
                type="next"
                @click="saveHostAction"
              />
              <CmkWizardButton v-else-if="currentStep === 1" type="next" />
            </template>
          </CmkWizardStep>

          <CmkWizardStep :index="2" :is-completed="() => currentStep > 2 || agentInstalled">
            <template #header>
              <CmkHeading> {{ _t('Download and install') }}</CmkHeading>
            </template>
            <template #content>
              <div v-if="currentStep === 2">
                <CmkCode
                  v-if="tab.installMsg && tab.installCmd"
                  :title="tab.installMsg"
                  :code_txt="tab.installCmd"
                  class="code"
                />
                <div
                  v-if="
                    tab.installUrl &&
                    !tab.installCmd &&
                    !(tab.installDebCmd && model === packageFormatDeb) &&
                    !(tab.installRpmCmd && model === packageFormatRpm) &&
                    !(tab.installTgzCmd && model === packageFormatTgz)
                  "
                  class="install_url__div"
                >
                  <CmkParagraph v-if="tab.installUrl.msg">{{ tab.installUrl.msg }}</CmkParagraph>
                  <CmkLinkCard
                    :title="tab.installUrl.title"
                    :url="tab.installUrl.url"
                    :icon-name="tab.installUrl.icon"
                    :open-in-new-tab="true"
                  />
                </div>
                <CmkCode
                  v-if="tab.installMsg && tab.installDebCmd && model === packageFormatDeb"
                  :title="tab.installMsg"
                  :code_txt="tab.installDebCmd"
                  class="code"
                />
                <CmkCode
                  v-if="tab.installMsg && tab.installRpmCmd && model === packageFormatRpm"
                  :title="tab.installMsg"
                  :code_txt="tab.installRpmCmd"
                  class="code"
                />
                <CmkCode
                  v-if="tab.installMsg && tab.installTgzCmd && model === packageFormatTgz"
                  :title="tab.installMsg"
                  :code_txt="tab.installTgzCmd"
                  class="code"
                />
              </div>
              <div v-else>
                <CmkParagraph>
                  {{ _t('Run this command to download and install the Checkmk agent.') }}
                </CmkParagraph>
              </div>
            </template>
            <template v-if="currentStep === 2" #actions>
              <CmkWizardButton type="next" :override-label="_t('Next step: Register agent')" />
              <CmkWizardButton type="previous" />
            </template>
          </CmkWizardStep>

          <CmkWizardStep :index="3" :is-completed="() => currentStep > 3 || !tab.registrationMsg">
            <template #header>
              <CmkHeading> {{ _t('Register agent') }}</CmkHeading>
            </template>
            <template #content>
              <div v-if="currentStep === 3">
                <div v-if="tab.registrationMsg && tab.registrationCmd">
                  <div class="register-heading-row">
                    <CmkParagraph>
                      {{
                        _t(
                          `Agent registration will establish trust between the Agent Controller
                    on the host and the Agent Receiver on the Checkmk server.`
                        )
                      }}
                    </CmkParagraph>
                  </div>
                  <CmkCode
                    :title="tab.registrationMsg"
                    :code_txt="tab.registrationCmd"
                    class="code"
                  />
                </div>
              </div>
              <div v-else>
                <CmkParagraph>
                  {{ _t('Run this command to register the Checkmk agent controller.') }}
                </CmkParagraph>
              </div>
            </template>
            <template v-if="currentStep === 3" #actions>
              <CmkWizardButton
                v-if="!isPushMode"
                type="finish"
                :override-label="closeButtonTitle"
                icon-name="connection_tests"
                @click="close"
              />
              <CmkWizardButton v-else type="next" />
              <CmkWizardButton type="previous" />
            </template>
          </CmkWizardStep>

          <CmkWizardStep v-if="isPushMode" :index="4" :is-completed="() => currentStep > 4">
            <template #header>
              <CmkHeading> {{ _t('Test connection') }}</CmkHeading>
            </template>
            <template #content>
              <CmkParagraph>
                {{
                  _t(`Test if you have configured everything correctly with pasting the following
                  command into the CLI of the target system.`)
                }}
              </CmkParagraph>
              <CmkCode v-if="currentStep === 4" code_txt="cmk-agent-ctl status" />
            </template>
            <template #actions>
              <CmkWizardButton type="finish" :override-label="closeButtonTitle" @click="close" />
              <CmkWizardButton type="previous" />
            </template>
          </CmkWizardStep>
        </CmkWizard>
      </CmkTabContent>
    </template>
  </CmkTabs>
</template>

<style scoped>
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

.code {
  margin-bottom: var(--dimension-7);
}

.register-heading-row {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: var(--dimension-4);
}

.save_host__div {
  margin-bottom: var(--spacing);
}

.install_url__div {
  margin-bottom: var(--spacing);
}

.agent_slideout__paragraph_host_exists {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
}
</style>
