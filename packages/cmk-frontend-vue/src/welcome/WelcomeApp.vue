<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { StageInformation, WelcomeCards } from 'cmk-shared-typing/typescript/welcome'
import { computed, ref } from 'vue'

import CmkScrollContainer from '@/components/CmkScrollContainer.vue'

import { refreshSidebarSnapin } from '@/sidebar/lib/snapin-refresh'
import NextSteps from '@/welcome/components/NextSteps.vue'
import OnboardingStepper from '@/welcome/components/OnboardingStepper.vue'
import ResourceLinksPanel from '@/welcome/components/ResourceLinksPanel.vue'
import { getWelcomeStageInformation, markStepAsComplete } from '@/welcome/components/steps/utils.ts'

import WelcomeBanner from './components/WelcomeBanner.vue'
import WelcomeFooter from './components/WelcomeFooter.vue'
import { type StepId, totalSteps } from './components/steps/stepComponents'

const props = defineProps<{
  cards: WelcomeCards
  stage_information: StageInformation
  is_start_url: boolean
}>()

const currentStageInformation = ref(props.stage_information)
const completedSteps = computed(() => currentStageInformation.value.finished.length)

async function stepCompleted(stepId: StepId): Promise<void> {
  await markStepAsComplete(props.cards.mark_step_completed, stepId).then(async () => {
    currentStageInformation.value =
      (await getWelcomeStageInformation(props.cards.get_stage_information)) ||
      currentStageInformation.value
  })

  // Notify sidebar to refresh the welcome snapin
  refreshSidebarSnapin('snapin_a_welcome')
}
</script>

<template>
  <CmkScrollContainer type="outer">
    <div class="welcome-app">
      <WelcomeBanner
        class="welcome-app__banner"
        :completed-steps="completedSteps"
        :total-steps="totalSteps"
      />
      <div class="welcome-app__panels">
        <div class="welcome-app__panel-left">
          <NextSteps v-if="completedSteps === totalSteps" :cards="cards" />
          <OnboardingStepper
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

.welcome-app__banner {
  margin-top: 32px;
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
