<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { StageInformation, WelcomeUrls } from 'cmk-shared-typing/typescript/welcome'

import usei18n from '@/lib/i18n'

import CmkBadge from '@/components/CmkBadge.vue'
import CmkButton from '@/components/CmkButton.vue'
import CmkIcon from '@/components/CmkIcon.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import StepsProgressBar from '../StepsProgressBar.vue'
import { totalSteps } from '../steps/stepComponents'

const { _t } = usei18n()

const props = defineProps<{
  urls: WelcomeUrls
  stage_information: StageInformation
}>()

interface CmkWindow extends Window {
  main: Window
}

const completedSteps = props.stage_information.finished.length

function openSlideIn() {
  const event = new CustomEvent('open-welcome-slide-in', {
    detail: {
      urls: props.urls,
      stage_information: props.stage_information
    }
  })
  ;(top!.frames as CmkWindow).main.dispatchEvent(event)
}

const completed = completedSteps === totalSteps
</script>

<template>
  <CmkParagraph v-if="completed" class="welcome-snapin-completed">
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
    class="welcome-snapin-progress-wrapper"
  />
  <CmkButton
    v-if="!completed"
    variant="secondary"
    class="welcome-snapin-continue"
    @click="openSlideIn"
  >
    {{ _t('Continue setup') }}
  </CmkButton>
  <CmkButton v-else variant="secondary" class="welcome-snapin-continue" @click="openSlideIn">
    {{ _t("What's next") }}
  </CmkButton>
</template>

<style scoped>
.welcome-snapin-completed {
  display: flex;
  flex-direction: row;
  align-items: center;
}

.welcome-snapin-progress-wrapper {
  display: flex;
  flex-direction: column;
}

.welcome-snapin-continue {
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
