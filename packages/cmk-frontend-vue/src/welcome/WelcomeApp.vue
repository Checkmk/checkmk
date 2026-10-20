<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { StageInformation, WelcomeCards } from 'cmk-shared-typing/typescript/welcome'
import CmkScrollContainer from 'cmk-ui-library/components/CmkScrollContainer.vue'
import CmkSpace from 'cmk-ui-library/components/CmkSpace.vue'
import CmkTabs, { CmkTab, CmkTabContent } from 'cmk-ui-library/components/CmkTabs'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

import { refreshSidebarSnapin } from '@/sidebar/lib/snapin-refresh'
import FurtherGuides from '@/welcome/components/FurtherGuides.vue'
import NextSteps from '@/welcome/components/NextSteps.vue'
import OnboardingStepper from '@/welcome/components/OnboardingStepper.vue'
import ResourceLinksPanel from '@/welcome/components/ResourceLinksPanel.vue'
import {
  type StepId,
  getWelcomeStageInformation,
  markStepAsComplete
} from '@/welcome/components/steps/utils.ts'

import WelcomeBanner from './components/WelcomeBanner.vue'
import WelcomeFooter from './components/WelcomeFooter.vue'
import { countCompletedSteps, totalSteps } from './components/steps/stepComponents'

const { _t } = usei18n()

const props = defineProps<{
  cards: WelcomeCards
  stage_information: StageInformation
  is_start_url: boolean
}>()

const currentStageInformation = ref(props.stage_information)
const completedSteps = computed(() => countCompletedSteps(currentStageInformation.value.finished))
const openedTab = ref<string>('explore')

async function stepCompleted(stepId: StepId): Promise<void> {
  await markStepAsComplete(props.cards.mark_step_completed, stepId).then(async () => {
    currentStageInformation.value =
      (await getWelcomeStageInformation(props.cards.get_stage_information)) ||
      currentStageInformation.value
  })

  refreshSidebarSnapin('a_welcome')
}
</script>

<template>
  <CmkScrollContainer type="outer">
    <div class="welcome-app">
      <WelcomeBanner :completed-steps="completedSteps" :total-steps="totalSteps" />
      <div class="welcome-app__panels">
        <div class="welcome-app__panel-left">
          <CmkTabs v-if="completedSteps === totalSteps" v-model="openedTab">
            <template #tabs>
              <CmkTab id="explore">{{ _t('To explore') }}</CmkTab>
              <CmkTab id="done">{{ _t('Done') }}</CmkTab>
            </template>
            <template #tab-contents>
              <CmkTabContent id="explore">
                <NextSteps
                  :cards="cards"
                  :finished-steps="currentStageInformation.finished"
                  @step-completed="stepCompleted"
                />
              </CmkTabContent>
              <CmkTabContent id="done">
                <OnboardingStepper
                  :cards="cards"
                  :finished-steps="currentStageInformation.finished"
                  :show-heading="false"
                  @step-completed="stepCompleted"
                />
                <CmkSpace />
                <FurtherGuides
                  :cards="cards"
                  :finished-steps="currentStageInformation.finished"
                  show="done"
                  @step-completed="stepCompleted"
                />
              </CmkTabContent>
            </template>
          </CmkTabs>
          <OnboardingStepper
            v-else
            :cards="cards"
            :finished-steps="currentStageInformation.finished"
            :show-heading="true"
            @step-completed="stepCompleted"
          />
        </div>
        <div class="welcome-app__panel-right">
          <ResourceLinksPanel :cards="cards" />
        </div>
      </div>
      <WelcomeFooter class="welcome-app__footer" :is_start_url="is_start_url" />
    </div>
  </CmkScrollContainer>
</template>

<style scoped>
.welcome-app {
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 20px);
  padding-right: 10px;
  padding-bottom: 10px;
}

.welcome-app__panels {
  display: flex;
  margin-top: var(--spacing);
}

.welcome-app__panel-left {
  margin-right: var(--spacing);
  flex: 2;
}

.welcome-app__panel-right {
  margin-left: auto;
  flex: 1;
}

.welcome-app__footer {
  margin-top: auto;
}
</style>
