<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from '@/components/CmkIcon.vue'
import type { LogStep, LogStepStatus } from './useBackgroundJobLog'
import CmkLoading from '@/components/CmkLoading.vue'

interface BackgroundJobLogDisplayProps {
  /** @property {LogStep} steps - List of steps*/
  steps: LogStep[]
  displayLoading?: boolean
}

const props = defineProps<BackgroundJobLogDisplayProps>()

const getIcon = (step: LogStep) => {
  const icons: Record<LogStepStatus, string> = {
    completed: 'checkmark',
    active: 'load-graph',
    pending: 'pending-task',
    error: 'cross'
  }
  return icons[step.status]
}
</script>
<template>
  <ul class="qs-background-job-log-display__list">
    <li v-for="(item, idx) in props.steps" :key="idx">
      <CmkIcon :name="getIcon(item)" variant="inline" size="medium" /> {{ item.title }}
    </li>
    <li v-if="!!props.displayLoading">
      <CmkLoading class="qs-background-job-loading-dots" />
    </li>
  </ul>
</template>

<style scoped>
.qs-background-job-loading-dots {
  padding-left: 25px;
}

.qs-background-job-log-display__list {
  padding-top: 7px;
  min-height: 40px;
  padding-left: 0px;
  line-height: 18px;
  list-style-position: inside;
  list-style-type: none;
}
.qs-background-job-log-display__list li {
  padding-top: 5px;
}
</style>
