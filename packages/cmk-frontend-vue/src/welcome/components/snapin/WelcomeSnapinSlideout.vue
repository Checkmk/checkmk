<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { StageInformation, WelcomeUrls } from 'cmk-shared-typing/typescript/welcome'
import { computed, onMounted, ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkButton from '@/components/CmkButton.vue'
import CmkIcon from '@/components/CmkIcon.vue'
import CmkSlideInDialog from '@/components/CmkSlideInDialog.vue'

import NextSteps from '@/welcome/components/NextSteps.vue'
import OnboardingStepper from '@/welcome/components/OnboardingStepper.vue'
import { getWelcomeStageInformation, markStepAsComplete } from '@/welcome/components/steps/utils.ts'

import { type StepId, totalSteps } from '../steps/stepComponents'

const { _t } = usei18n()

const urls = ref<WelcomeUrls>()
const stageInformation = ref<StageInformation>()
const slideInOpen = ref(false)
const nextStepsTitle = _t('Next steps with Checkmk')
const firstStepsTitle = _t('First steps with Checkmk')
const slideInTitle = ref(nextStepsTitle)

const completedSteps = computed(() => stageInformation.value?.finished.length || 0)
const completed = computed(() => completedSteps.value === totalSteps)

function slideInEventListener(event: CustomEvent): void {
  urls.value = event.detail.urls
  stageInformation.value = event.detail.stage_information
  slideInTitle.value = completed.value ? nextStepsTitle : firstStepsTitle
  openSlideIn()
}

async function stepCompleted(stepId: StepId): Promise<void> {
  if (urls.value) {
    await markStepAsComplete(urls.value.mark_step_completed, stepId).then(async () => {
      if (urls.value) {
        stageInformation.value =
          (await getWelcomeStageInformation(urls.value.get_stage_information)) ||
          stageInformation.value
      }
    })
  }
}

onMounted(() => {
  // TODO: remove as unknown as EventListener once https://github.com/Microsoft/TypeScript/issues/28357 is fixed
  window.addEventListener('open-welcome-slide-in', slideInEventListener as unknown as EventListener)
})

function openFullView() {
  window.open('welcome.py', 'main')
  closeSlideIn()
}

function closeSlideIn() {
  slideInOpen.value = false
}

function openSlideIn() {
  slideInOpen.value = true
}
</script>

<template>
  <CmkSlideInDialog
    :open="slideInOpen"
    :header="{ title: slideInTitle, closeButton: true }"
    @close="closeSlideIn"
  >
    <CmkButton variant="secondary" class="full-view-button" @click="() => openFullView()">
      <CmkIcon variant="inline" name="frameurl" />
      {{ _t('Open full view') }}
    </CmkButton>
    <OnboardingStepper
      v-if="!completed && urls"
      :urls="urls"
      :finished-steps="stageInformation?.finished || []"
      :show-heading="false"
      @step-completed="stepCompleted"
    />
    <NextSteps v-else-if="urls" :urls="urls" />
  </CmkSlideInDialog>
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.full-view-button {
  margin-bottom: var(--spacing);
}
</style>
