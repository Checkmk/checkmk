<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import usei18n from '@/lib/i18n'
import usePersistentRef from '@/lib/usePersistentRef'

import CmkCode from '@/components/CmkCode.vue'
import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'
import CmkSlideInDialog from '@/components/CmkSlideInDialog.vue'
import CmkSpace from '@/components/CmkSpace.vue'
import CmkTab from '@/components/CmkTabs/CmkTab.vue'
import CmkTabContent from '@/components/CmkTabs/CmkTabContent.vue'
import CmkTabs from '@/components/CmkTabs/CmkTabs.vue'
import CmkWizard from '@/components/CmkWizard/CmkWizard.vue'
import CmkWizardButton from '@/components/CmkWizard/CmkWizardButton.vue'
import CmkWizardStep from '@/components/CmkWizard/CmkWizardStep.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import { finalStepText, tabs } from './FirstHostSlideoutContent'
import { CseOnboardingApiClient } from './onboarding-api-client'

const { _t } = usei18n()

const slideInOpen = defineModel<boolean>({ required: true })
const openedTab = usePersistentRef<string | number>('first-host-slideout-opened-tab', 'deb')
const currentStep = ref<number>(1)
const onboardingApiClient = new CseOnboardingApiClient('api/v1/')
const agentSecret = ref<string | null>(null)

function onClose() {
  slideInOpen.value = false
  setTimeout(() => (currentStep.value = 1), 300)
}

function goToHostOverview() {
  window.location.href = 'wato.py?mode=folder'
}

onMounted(async () => {
  try {
    if (!agentSecret.value) {
      agentSecret.value = (await onboardingApiClient.getAgentSecret()).secret
    }
  } catch (e) {
    console.error('Failed to fetch agent download information', e)
  }
})
</script>

<template>
  <CmkSlideInDialog
    :header="{
      title: _t('Add your first host'),
      closeButton: true
    }"
    :open="slideInOpen"
    @close="onClose"
  >
    <CmkTabs v-model="openedTab" @update:model-value="() => (currentStep = 1)">
      <template #tabs>
        <CmkTab
          v-for="tab in tabs"
          :id="tab.id"
          :key="tab.id"
          class="welcome-first-host-slideout__tabs"
        >
          <CmkHeading type="h2">
            <CmkIcon class="welcome-first-host-slideout__tab-icon" :name="tab.icon" />
            {{ tab.title }}
          </CmkHeading>
        </CmkTab>
      </template>
      <template #tab-contents>
        <CmkTabContent v-for="tab in tabs" :id="tab.id" :key="tab.id">
          <CmkWizard v-model="currentStep" mode="guided">
            <CmkWizardStep
              v-for="step in tab.steps"
              :key="tab.id + step.title"
              :index="step.stepNumber"
              :is-completed="() => currentStep > step.stepNumber"
            >
              <template #header>
                <CmkHeading> {{ step.title }}</CmkHeading>
              </template>

              <template #content>
                <CmkParagraph>
                  {{ step.description_top }}
                </CmkParagraph>
                <CmkCode
                  :code_txt="
                    step.code.replace(
                      '[AGENT_DOWNLOAD_SECRET]',
                      agentSecret || '<agent-download-secret>'
                    )
                  "
                  class="welcome-first-host-slideout__code"
                />
                <CmkParagraph v-if="step.description_bottom">
                  {{ step.description_bottom }}
                </CmkParagraph>
                <CmkSpace></CmkSpace>
              </template>

              <template #actions>
                <CmkWizardButton type="next" />
                <CmkWizardButton v-if="step.stepNumber > 1" type="previous" />
              </template>
            </CmkWizardStep>
            <CmkWizardStep
              :index="tab.steps.length + 1"
              :is-completed="() => currentStep > tab.steps.length + 1"
            >
              <template #header>
                <CmkHeading> {{ _t('View your newly added host') }}</CmkHeading>
              </template>

              <template #content>
                <CmkParagraph>{{ finalStepText }}</CmkParagraph>
                <CmkSpace></CmkSpace>
              </template>

              <template #actions>
                <CmkWizardButton
                  type="finish"
                  :override-label="_t('View hosts')"
                  @click="goToHostOverview"
                />
                <CmkWizardButton type="previous" />
              </template>
            </CmkWizardStep>
          </CmkWizard>
        </CmkTabContent>
      </template>
    </CmkTabs>
  </CmkSlideInDialog>
</template>

<style scoped>
.welcome-first-host-slideout__tabs {
  display: flex;
  flex-direction: row;
  align-items: center;

  > h2 {
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: row;
    align-items: center;

    .welcome-first-host-slideout__tab-icon {
      margin-right: var(--dimension-4);
    }
  }
}

.welcome-first-host-slideout__code {
  width: calc(100% - 50px);
}
</style>
