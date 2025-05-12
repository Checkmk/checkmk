<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CompositeWidget from './components/quick-setup/widgets/CompositeWidget.vue'
import type { QuickSetupStageWidgetContentProps } from './types'
import type { StageData } from '@/quick-setup/components/quick-setup/widgets/widget_types'
import { BackgroundJobLogDisplay } from '@/quick-setup/components/BackgroundJobLog'

const props = defineProps<QuickSetupStageWidgetContentProps>()
const emit = defineEmits(['update'])
const internalUserInput: StageData = (props.userInput as StageData) || {}

const updateData = (id: string, value: object) => {
  internalUserInput[id] = value
  emit('update', internalUserInput)
}
</script>

<template>
  <CompositeWidget
    v-if="components.length > 0"
    :items="components"
    :data="internalUserInput"
    :errors="formSpecErrors || {}"
    @update="updateData"
  />
  <BackgroundJobLogDisplay
    v-if="props.backgroundJobLog && props.backgroundJobLog.length > 0"
    :steps="backgroundJobLog!"
    :display-loading="props.isBackgroundJobRunning"
  />
</template>

<style scoped>
.qs-stage-widget-content__background-job-list {
  padding-top: 20px;
}
</style>
