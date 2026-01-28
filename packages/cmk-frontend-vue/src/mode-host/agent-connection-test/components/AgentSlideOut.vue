<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, watch } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkButton from '@/components/CmkButton.vue'
import CmkCode from '@/components/CmkCode.vue'
import CmkDialog from '@/components/CmkDialog.vue'
import CmkIcon from '@/components/CmkIcon'
import CmkLinkCard from '@/components/CmkLinkCard'
import CmkTabs, { CmkTab, CmkTabContent } from '@/components/CmkTabs'
import CmkToggleButtonGroup from '@/components/CmkToggleButtonGroup.vue'
import CmkWizard, { CmkWizardButton, CmkWizardStep } from '@/components/CmkWizard'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import type { AgentSlideOutTabs } from '../lib/type_def'
import RegisterAgent from './steps/RegisterAgent.vue'

const props = defineProps<{
  dialogMsg: TranslatedString
  tabs: AgentSlideOutTabs[]
  allAgentsUrl: string
  closeButtonTitle: TranslatedString
  saveHost: boolean
  hostExists?: boolean
  setupError?: boolean
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
    <CmkIcon name="connection-tests" />
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
  <CmkDialog
    :message="dialogMsg"
    :dismissal_button="{ title: _t('Do not show again'), key: 'agent_slideout' }"
  />
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
        <CmkToggleButtonGroup
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
              <div v-if="setupError" class="save_host__div">
                <CmkParagraph class="agent_slideout__paragraph_host_exists">
                  <CmkIcon name="cross" />
                  {{
                    _t(
                      `Could not save host "${hostName}". Close the slideout and review your input.`
                    )
                  }}
                </CmkParagraph>
              </div>
              <div v-else-if="!saveHost && hostExists" class="save_host__div">
                <CmkParagraph class="agent_slideout__paragraph_host_exists">
                  <CmkIcon name="checkmark" />
                  {{ _t(`Host "${hostName}" exists`) }}
                </CmkParagraph>
              </div>
            </template>
            <template #actions>
              <CmkButton v-if="setupError" :title="_t('Close and revise form')" @click="close">
                <CmkIcon name="edit" />
                {{ _t('Close & review') }}
              </CmkButton>
              <CmkWizardButton
                v-if="saveHost && !setupError"
                :override-label="_t('Save host & next step')"
                type="next"
                @click="saveHostAction"
              />
              <CmkWizardButton v-else-if="currentStep === 1 && !setupError" type="next" />
            </template>
          </CmkWizardStep>

          <CmkWizardStep :index="2" :is-completed="() => currentStep > 2 || agentInstalled">
            <template #header>
              <CmkHeading> {{ _t('Download and install') }}</CmkHeading>
            </template>
            <template #content>
              <div v-if="currentStep === 2">
                <CmkParagraph>{{ tab.installMsg }}</CmkParagraph>
                <CmkCode
                  v-if="tab.installMsg && tab.installCmd"
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
                  :code_txt="tab.installDebCmd"
                  class="code"
                />
                <CmkCode
                  v-if="tab.installMsg && tab.installRpmCmd && model === packageFormatRpm"
                  :code_txt="tab.installRpmCmd"
                  class="code"
                />
                <CmkCode
                  v-if="tab.installMsg && tab.installTgzCmd && model === packageFormatTgz"
                  :code_txt="tab.installTgzCmd"
                  class="code"
                />
              </div>
            </template>
            <template v-if="currentStep === 2" #actions>
              <CmkWizardButton type="next" :override-label="_t('Next step: Register agent')" />
              <CmkWizardButton type="previous" />
            </template>
          </CmkWizardStep>

          <RegisterAgent
            :index="3"
            :is-completed="() => currentStep > 3 || !tab.registrationMsg"
            :tab="tab"
            :is-push-mode="isPushMode"
            :close-button-title="closeButtonTitle"
            :host-name="hostName"
            @close="close"
          ></RegisterAgent>

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

.code {
  margin: var(--dimension-5) 0 var(--dimension-7);
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
