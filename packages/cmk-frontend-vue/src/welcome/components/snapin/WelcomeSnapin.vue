<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { StageInformation, WelcomeCards } from 'cmk-shared-typing/typescript/welcome'
import CmkBadge from 'cmk-ui-library/components/CmkBadge.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

import StepsProgressBar from '../StepsProgressBar.vue'
import { countCompletedSteps, totalSteps } from '../steps/stepComponents'
import WelcomeSnapinSlideout from './WelcomeSnapinSlideout.vue'

const { _t } = usei18n()

const props = defineProps<{
  cards: WelcomeCards
  stage_information: StageInformation
}>()

const currentStageInformation = ref(props.stage_information)
const completedSteps = computed(() => countCompletedSteps(currentStageInformation.value.finished))
const completed = computed(() => completedSteps.value === totalSteps)
const slideoutOpen = ref<boolean>(false)

async function openSlideIn() {
  slideoutOpen.value = true
}

async function closeSlideIn() {
  slideoutOpen.value = false
}
</script>

<template>
  <CmkParagraph v-if="completed" class="welcome-snapin__completed">
    <CmkBadge color="success" type="fill" shape="circle" size="small">
      <CmkIcon name="checkmark" size="large"></CmkIcon>
    </CmkBadge>

    {{ _t('All steps completed') }}
  </CmkParagraph>
  <StepsProgressBar
    v-else
    :completed-steps="completedSteps"
    :total-steps="totalSteps"
    :hide-heading="true"
    :flex-column="true"
    size="small"
    class="welcome-snapin__progress-wrapper"
  />

  <CmkButton
    v-if="!slideoutOpen"
    variant="success"
    class="welcome-snapin__continue"
    @click="openSlideIn"
  >
    {{ completed ? _t("What's next") : _t('Continue exploration') }}
  </CmkButton>
  <CmkButton v-else variant="success" class="welcome-snapin__continue" @click="closeSlideIn">
    {{ _t('Close') }}
  </CmkButton>
  <WelcomeSnapinSlideout
    v-model:slide-in-open="slideoutOpen"
    v-model:stage-information="currentStageInformation"
    :cards="cards"
  ></WelcomeSnapinSlideout>
</template>

<style scoped>
.welcome-snapin__completed {
  display: flex;
  flex-direction: row;
  align-items: center;
}

.welcome-snapin__progress-wrapper {
  display: flex;
  flex-direction: column;
}

.welcome-snapin__continue {
  display: flex;
  width: 100%;
  margin-top: var(--spacing);
}
</style>
