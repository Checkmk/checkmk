<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { StageInformation, WelcomeCards } from 'cmk-shared-typing/typescript/welcome'
import { computed, ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkBadge from '@/components/CmkBadge.vue'
import CmkButton from '@/components/CmkButton.vue'
import CmkIcon from '@/components/CmkIcon'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import StepsProgressBar from '../StepsProgressBar.vue'
import { totalSteps } from '../steps/stepComponents'
import WelcomeSnapinSlideout from './WelcomeSnapinSlideout.vue'

const { _t } = usei18n()

const props = defineProps<{
  cards: WelcomeCards
  stage_information: StageInformation
}>()

const currentStageInformation = ref(props.stage_information)
const completedSteps = computed(() => currentStageInformation.value.finished.length)
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
    variant="secondary"
    class="welcome-snapin__continue"
    @click="openSlideIn"
  >
    {{ completed ? _t("What's next") : _t('Continue exploration') }}
  </CmkButton>
  <CmkButton v-else variant="secondary" class="welcome-snapin__continue" @click="closeSlideIn">
    {{ _t('Close') }}
  </CmkButton>
  <WelcomeSnapinSlideout
    v-model="slideoutOpen"
    :cards="cards"
    :stage_information="stage_information"
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
  height: var(--dimension-10);
  background: var(--success);
  color: var(--black);
  width: 100%;
  align-items: center;
  justify-content: center;
  border-radius: var(--border-radius);
  margin-top: var(--spacing);
  font-weight: var(--font-weight-bold);

  &:hover {
    background: var(--color-corporate-green-40);
  }
}
</style>
