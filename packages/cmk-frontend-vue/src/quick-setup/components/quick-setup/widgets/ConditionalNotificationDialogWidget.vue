<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { ConditionalNotificationDialogWidgetProps } from '@/quick-setup/components/quick-setup/widgets/widget_types'
import type { StageData } from '@/quick-setup/components/quick-setup/widgets/widget_types.ts'
import { inject, computed } from 'vue'
import { formDataKey } from '@/quick-setup/keys.ts'
import ConditionalNotificationStageWidget from '@/quick-setup/components/quick-setup/widgets/ConditionalNotificationStageWidget.vue'

const props = defineProps<ConditionalNotificationDialogWidgetProps>()

const formData = inject(formDataKey)

const computedCondition = computed(() => {
  if (props.target === 'recipient') {
    return showConditionalNotificationDialogRecipientWidget
  }
  return showConditionalNotificationDialogServiceFilterWidget
})

function showConditionalNotificationDialogServiceFilterWidget(
  formData: { [key: number]: StageData } | undefined
) {
  if (!formData) {
    return false
  }
  for (const stageValue of Object.values(formData)) {
    if (!('triggering_events' in stageValue)) {
      continue
    }

    const triggeringEvents = stageValue['triggering_events']
    if (Array.isArray(triggeringEvents)) {
      if (0 in triggeringEvents && triggeringEvents[0] === 'all_events') {
        return true
      }

      if (
        0 in triggeringEvents &&
        triggeringEvents[0] === 'specific_events' &&
        1 in triggeringEvents &&
        'host_events' in triggeringEvents[1]
      ) {
        return true
      }
    }
  }
  return false
}

function showConditionalNotificationDialogRecipientWidget(
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
    :condition="computedCondition(formData)"
    :items="props.items"
    :data="props?.data || {}"
    :errors="props.errors || {}"
  />
</template>
