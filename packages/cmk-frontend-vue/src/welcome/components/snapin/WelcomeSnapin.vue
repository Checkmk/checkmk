<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { StageInformation, WelcomeUrls } from 'cmk-shared-typing/typescript/welcome'
import { totalSteps } from '../steps/stepComponents'
import StepsProgressBar from '../StepsProgressBar.vue'
import usei18n from '@/lib/i18n'
import CmkIcon from '@/components/CmkIcon.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'
import CmkBadge from '@/components/CmkBadge.vue'

const { t } = usei18n('welcome-snapin')

const props = defineProps<{
  urls: WelcomeUrls
  stage_information: StageInformation
}>()

const completedSteps = props.stage_information.finished.length
</script>

<template>
  <CmkParagraph v-if="completedSteps === totalSteps" class="welcome-snapin-completed">
    <CmkBadge color="success" type="fill" shape="circle" size="small">
      <CmkIcon name="checkmark" size="large"></CmkIcon>
    </CmkBadge>

    {{ t('all-steps-completed', 'All steps completed') }}
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
  <a href="welcome.py" target="main" class="welcome-snapin-whats-next">{{
    t('whats-new', "What's next?")
  }}</a>
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
.welcome-snapin-whats-next {
  display: flex;
  height: var(--dimension-height-10);
  background: var(--success);
  color: var(--black);
  width: 100%;
  align-items: center;
  justify-content: center;
  border-radius: var(--border-radius);
  margin-top: var(--spacing);
  font-weight: var(--font-weight-bold);
  font-size: var(--fonr-size-large);

  &:hover {
    background: var(--color-corporate-green-40);
  }
}
</style>
