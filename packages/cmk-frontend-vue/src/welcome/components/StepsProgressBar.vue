<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import usei18n from '@/lib/i18n'
import CmkHeading2 from '@/components/typography/CmkHeading2.vue'
import CmkBody from '@/components/typography/CmkBodyText.vue'
import CmkProgressbar from '@/components/CmkProgressbar.vue'

const { t } = usei18n('steps-progress-bar')

export interface StepsProgressBarProps {
  completedSteps?: number
  totalSteps?: number
}

const { completedSteps = 1, totalSteps = 5 } = defineProps<StepsProgressBarProps>()
</script>

<template>
  <div class="steps-progress-bar">
    <CmkHeading2>{{ t('your-progress', 'Your progress') }}</CmkHeading2>
    <div class="steps-progress-bar__content">
      <CmkBody>
        {{ completedSteps }}/{{ totalSteps }}
        {{ t('steps-complete', 'Steps complete') }}
      </CmkBody>
      <CmkProgressbar
        class="steps-progress-bar__bar"
        :value="completedSteps"
        :max="totalSteps"
        size="small"
      />
    </div>
  </div>
</template>

<style scoped>
.steps-progress-bar {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-direction: column;
  align-items: start;
}

.steps-progress-bar__content {
  display: flex;
  gap: 8px;
  align-items: center;
  width: 100%;
}

.steps-progress-bar__bar {
  max-width: 480px;
  flex: 1;
}
</style>
