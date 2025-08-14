<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { StageInformation, WelcomeUrls } from 'cmk-shared-typing/typescript/welcome'
import { totalSteps } from '../steps/stepComponents'
import usei18n from '@/lib/i18n'
import CmkIcon from '@/components/CmkIcon.vue'
import OnboardingStepper from '@/welcome/components/OnboardingStepper.vue'
import CmkSlideInDialog from '@/components/CmkSlideInDialog.vue'
import { onMounted, ref } from 'vue'
import CmkButton from '@/components/CmkButton.vue'
import NextSteps from '@/welcome/components/NextSteps.vue'

const { _t } = usei18n()

const urls = ref<WelcomeUrls>()
const stageInformation = ref<StageInformation>()
const completedSteps = ref<number>(0)
const slideInOpen = ref(false)
const completed = ref(false)
const nextStepsTitle = _t('Next steps with Checkmk')
const firstStepsTitle = _t('First steps with Checkmk')
const slideInTitle = ref(nextStepsTitle)

function slideInEventListener(event: CustomEvent): void {
  urls.value = event.detail.urls
  stageInformation.value = event.detail.stage_information
  completedSteps.value = stageInformation.value?.finished.length || 0
  completed.value = completedSteps.value === totalSteps
  slideInTitle.value = completed.value ? nextStepsTitle : firstStepsTitle
  openSlideIn()
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
    />
    <NextSteps v-else-if="urls" :urls="urls" />
  </CmkSlideInDialog>
</template>

<style scoped>
.full-view-button {
  margin-bottom: var(--spacing);
}
</style>
