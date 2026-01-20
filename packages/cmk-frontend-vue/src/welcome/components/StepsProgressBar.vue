<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkProgressbar from '@/components/CmkProgressbar.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import { type Sizes } from '../../components/CmkProgressbar.vue'

const { _t } = usei18n()

export interface StepsProgressBarProps {
  completedSteps?: number
  totalSteps?: number
  hideHeading?: boolean
  flexColumn?: boolean
  size?: Sizes
}

const { completedSteps = 1, totalSteps = 5 } = defineProps<StepsProgressBarProps>()
const progressLabel = computed(() => {
  return (
    (totalSteps === completedSteps ? `${totalSteps} ` : `${completedSteps}/${totalSteps} `) +
    _t('Topics explored')
  )
})
</script>

<template>
  <div class="steps-progress-bar">
    <CmkHeading v-if="!hideHeading" type="h4">{{ _t('Your progress') }}</CmkHeading>
    <div class="steps-progress-bar__content" :class="{ 'flex-column': flexColumn }">
      <CmkParagraph>
        {{ progressLabel }}
      </CmkParagraph>
      <CmkProgressbar
        class="steps-progress-bar__bar"
        :class="{ 'flex-column': flexColumn }"
        :value="completedSteps"
        :max="totalSteps"
        :size="size ? size : 'medium'"
      />
    </div>
  </div>
</template>

<style scoped>
/* stylelint-disable checkmk/vue-bem-naming-convention */
.steps-progress-bar {
  display: flex;
  gap: 4px;
  flex-direction: column;
  align-items: start;
}

.steps-progress-bar__content {
  display: flex;
  gap: 8px;
  align-items: center;
  width: 100%;

  &.flex-column {
    flex-direction: column;
    align-items: flex-start;
  }
}

.steps-progress-bar__bar {
  max-width: 480px;
  width: 100%;
  flex: 1;

  &.flex-column {
    flex: none;
  }
}
</style>
