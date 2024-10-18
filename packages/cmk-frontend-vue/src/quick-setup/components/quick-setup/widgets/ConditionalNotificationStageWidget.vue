<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CompositeWidget from '@/quick-setup/components/quick-setup/widgets/CompositeWidget.vue'
import { computed, inject } from 'vue'
import { formDataKey } from '@/quick-setup/keys'
import type { ConditionalNotificationStageWidgetProps } from '@/quick-setup/components/quick-setup/widgets/widget_types'

const props = defineProps<ConditionalNotificationStageWidgetProps>()
const emits = defineEmits(['update'])

const updateData = (id: string, value: object) => {
  emits('update', id, value)
}

const formData = inject(formDataKey)

const conditionKeyExistsInPreviousStages = computed(() => {
  if (!formData) {
    return false
  }
  for (const stageValue of Object.values(formData.value)) {
    for (const subStageKey in stageValue) {
      if (props.conditionKey in stageValue[subStageKey]!) {
        return true
      }
    }
  }
  return false
})
</script>

<template>
  <div v-if="conditionKeyExistsInPreviousStages">
    <CompositeWidget
      :items="props.items"
      :data="props?.data || {}"
      :errors="props.errors || {}"
      @update="updateData"
    />
  </div>
</template>
