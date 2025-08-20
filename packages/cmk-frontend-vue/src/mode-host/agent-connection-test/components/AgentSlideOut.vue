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
  install_msg?: string
  install_cmd?: string | undefined
  install_deb_cmd?: string
  install_rpm_cmd?: string
  install_tgz_cmd?: string | undefined
  registration_msg?: string
  registration_cmd?: string
  install_url?: InstallUrl | undefined
  toggle_button_options?: PackageOptions
}

export interface InstallUrl {
  title: string
  url: string
  msg: string
  icon?: string
}

const props = defineProps<{
  dialog_msg: string
  tabs: AgentSlideOutTabs[]
  all_agents_url: string
  close_button_title: string
  save_host: boolean
  agent_installed: boolean
  host_name: string
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
function saveHost() {
  sessionStorage.setItem('reopenSlideIn', 'true')
  sessionStorage.setItem('slideInModelState', model.value)
  sessionStorage.setItem('slideInTabState', openedTab.value)
  cmk.page_menu.form_submit('edit_host', 'save_and_edit')
}
const currentStep = ref(getInitStep())
function getInitStep() {
  if (props.save_host) {
    return 1
  }
  if (!props.agent_installed) {
    return 2
  }
  return 3
}
</script>

<template>
  <CmkButton :title="close_button_title" class="close_and_test" @click="close">
    <CmkIcon name="connection_tests" />
    {{ close_button_title }}
  </CmkButton>
  <CmkButton
    :title="_t('View all agents')"
    class="all_agents"
    @click="() => openAllAgentsPage(all_agents_url)"
  >
    <CmkIcon name="frameurl" />
    {{ _t('View all agents') }}
  </CmkButton>
  <CmkDialog :message="dialog_msg" :dismissal_button="{ title: 'Do not show again', key: 'key' }" />
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
          v-if="tab.toggle_button_options"
          v-model="model"
          :options="tab.toggle_button_options"
        />
        <CmkWizard v-model="currentStep" mode="guided">
          <CmkWizardStep :index="1" :is-completed="() => currentStep > 1 || !save_host">
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
              <div v-if="!save_host" class="save_host__div">
                <CmkParagraph class="agent_slideout__paragraph_host_exists">
                  <CmkIcon name="checkmark" />
                  {{ _t(`Host "${host_name}" exists`) }}
                </CmkParagraph>
              </div>
            </template>
            <template #actions>
              <CmkWizardButton
                v-if="save_host"
                :override-label="_t('Save host & next step')"
                type="next"
                @click="saveHost"
              />
              <CmkWizardButton v-else-if="currentStep === 1" type="next" />
            </template>
          </CmkWizardStep>

          <CmkWizardStep :index="2" :is-completed="() => currentStep > 2 || agent_installed">
            <template #header>
              <CmkHeading> {{ _t('Download and install') }}</CmkHeading>
            </template>
            <template #content>
              <div v-if="currentStep === 2">
                <CmkCode
                  v-if="tab.install_msg && tab.install_cmd"
                  :title="tab.install_msg"
                  :code_txt="tab.install_cmd"
                  class="code"
                />
                <div
                  v-if="
                    tab.install_url &&
                    !tab.install_cmd &&
                    !(tab.install_deb_cmd && model === packageFormatDeb) &&
                    !(tab.install_rpm_cmd && model === packageFormatRpm) &&
                    !(tab.install_tgz_cmd && model === packageFormatTgz)
                  "
                  class="install_url__div"
                >
                  <CmkParagraph v-if="tab.install_url.msg">{{ tab.install_url.msg }}</CmkParagraph>
                  <CmkLinkCard
                    :title="tab.install_url.title"
                    :url="tab.install_url.url"
                    :icon-name="tab.install_url.icon"
                    :open-in-new-tab="true"
                  />
                </div>
                <CmkCode
                  v-if="tab.install_msg && tab.install_deb_cmd && model === packageFormatDeb"
                  :title="tab.install_msg"
                  :code_txt="tab.install_deb_cmd"
                  class="code"
                />
                <CmkCode
                  v-if="tab.install_msg && tab.install_rpm_cmd && model === packageFormatRpm"
                  :title="tab.install_msg"
                  :code_txt="tab.install_rpm_cmd"
                  class="code"
                />
                <CmkCode
                  v-if="tab.install_msg && tab.install_tgz_cmd && model === packageFormatTgz"
                  :title="tab.install_msg"
                  :code_txt="tab.install_tgz_cmd"
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
              <div class="agent_slideout__actions">
                <CmkWizardButton type="next" :override-label="_t('Next step: Register agent')" />
                <CmkWizardButton type="previous" />
              </div>
            </template>
          </CmkWizardStep>

          <CmkWizardStep :index="3" :is-completed="() => currentStep > 3 || !tab.registration_msg">
            <template #header>
              <CmkHeading> {{ _t('Register agent') }}</CmkHeading>
            </template>
            <template #content>
              <div v-if="currentStep === 3">
                <div v-if="tab.registration_msg && tab.registration_cmd">
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
                    :title="tab.registration_msg"
                    :code_txt="tab.registration_cmd"
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
              <div class="agent_slideout__actions">
                <CmkWizardButton
                  type="finish"
                  :override-label="close_button_title"
                  icon-name="connection_tests"
                  @click="close"
                />
                <CmkWizardButton type="previous" />
              </div>
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

.agent_slideout__actions {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: var(--dimension-4);
}

.agent_slideout__paragraph_host_exists {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
}
</style>
