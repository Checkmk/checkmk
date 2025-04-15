<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { CompositeWidgetProps } from '@/quick-setup/components/quick-setup/widgets/widget_types'
import type { StageData } from '@/quick-setup/components/quick-setup/widgets/widget_types.ts'
import { inject } from 'vue'
import { formDataKey } from '@/quick-setup/keys.ts'
import ConditionalNotificationStageWidget from '@/quick-setup/components/quick-setup/widgets/ConditionalNotificationStageWidget.vue'

const props = defineProps<CompositeWidgetProps>()

const formData = inject(formDataKey)

function showConditionalNotificationDialogWidget(
  formData: { [key: number]: StageData } | undefined
) {
  if (!formData) {
    return false
  }

  for (const stageValue of Object.values(formData)) {
    if (!('notification_method' in stageValue)) {
      continue
    }

    const notificationMethod = stageValue['notification_method']
    if (!('notification_effect' in notificationMethod)) {
      return false
    }

    const notificationEffect = notificationMethod['notification_effect'] as Record<
      number,
      string | string[]
    >
    const method = notificationEffect?.[1]?.[0] || 'mail'
    if (method === 'mail' || method === 'asciimail') {
      return false
    }
  }
  return true
}
</script>

<template>
  <ConditionalNotificationStageWidget
    :condition="showConditionalNotificationDialogWidget(formData)"
    :items="props.items"
    :data="props?.data || {}"
    :errors="props.errors || {}"
  />
</template>
