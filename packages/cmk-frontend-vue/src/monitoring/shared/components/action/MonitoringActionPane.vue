<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed } from 'vue'

import type { HostRef } from '@/monitoring/shared/api/types'

import type { ActionFeedback } from './ActionFeedback.vue'
import ActionFormPane from './ActionFormPane.vue'
import type { MonitoringActionRegistry } from './registry'

const props = defineProps<{
  actionId: string
  actions: MonitoringActionRegistry
  targets: HostRef[]
}>()

const emit = defineEmits<{
  (event: 'feedback', result: ActionFeedback): void
  (event: 'cancel'): void
}>()

const action = computed(() => props.actions[props.actionId])
const initialValues = computed(() => action.value?.defaultValues())

async function onSubmit(values: unknown): Promise<void> {
  const current = action.value
  if (!current) {
    return
  }
  emit('feedback', await current.perform(props.targets, values))
}
</script>

<template>
  <ActionFormPane
    v-if="action"
    :key="actionId"
    :title="action.title"
    :subtitle="action.subtitle(targets.length)"
    :submit-label="action.submitLabel"
    :form="action.form"
    :initial-values="initialValues"
    @submit="onSubmit"
    @cancel="emit('cancel')"
  />
</template>
