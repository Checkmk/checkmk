<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import WelcomeBanner from './components/WelcomeBanner.vue'
import WelcomeFooter from './components/WelcomeFooter.vue'
import ResourceLinksPanel from '@/welcome/components/ResourceLinksPanel.vue'
import NextSteps from '@/welcome/components/NextSteps.vue'
import type { WelcomeUrls, StageInformation } from 'cmk-shared-typing/typescript/welcome'
import OnboardingStepper from '@/welcome/components/OnboardingStepper.vue'

const props = defineProps<{
  urls: WelcomeUrls
  stage_information: StageInformation
  is_start_url: boolean
}>()

const completedSteps = props.stage_information.finished.length
const totalSteps = props.stage_information.total
</script>

<template>
  <div class="welcome-app">
    <WelcomeBanner :completed-steps="completedSteps" :total-steps="totalSteps" />
    <div class="welcome-app__panels">
      <div class="welcome-app__panel-left">
        <NextSteps v-if="completedSteps === totalSteps" :urls="urls" />
        <OnboardingStepper
          :urls="urls"
          :finished-steps="stage_information.finished"
          :total-steps="stage_information.total"
        ></OnboardingStepper>
      </div>
      <div class="welcome-app__panel-right">
        <ResourceLinksPanel :urls="urls" />
      </div>
    </div>
    <WelcomeFooter class="welcome-app__footer" :is_start_url="is_start_url" />
  </div>
</template>

<style scoped>
.welcome-app {
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 20px);
}
.welcome-app__panels {
  display: flex;
  margin-top: var(--spacing);
}
.welcome-app__panel-left {
  margin-right: var(--spacing);
  width: 100%;
}
.welcome-app__panel-right {
  margin-left: auto;
}
.welcome-app__footer {
  margin-top: auto;
}
</style>
