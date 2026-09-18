<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts" generic="Target">
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, inject, provide } from 'vue'

import { MONITORING_SERVICE } from '@/monitoring/shared/components/MonitoringTableContext'

import type { ActionFeedback } from './ActionFeedback.vue'
import ActionFormPane from './ActionFormPane.vue'
import type { MonitoringActionRegistry } from './registry'
import { ACTION_TARGET_COUNT } from './types'

const props = withDefaults(
  defineProps<{
    actionId: string
    actions: MonitoringActionRegistry<Target>
    targets: Target[]
    indent?: boolean | undefined
    showCount?: boolean | undefined
    showClose?: boolean | undefined
    /** Relates the selection to the loaded rows, e.g. "Selected services: 2 | Total services: 12". */
    countsLabel?: ((selected: number, total: number) => TranslatedString) | undefined
  }>(),
  { showCount: true }
)

const emit = defineEmits<{
  (event: 'feedback', result: ActionFeedback): void
  (event: 'cancel'): void
}>()

const monitoringService = inject(MONITORING_SERVICE, undefined)

provide(
  ACTION_TARGET_COUNT,
  computed(() => props.targets.length)
)

const action = computed(() => props.actions[props.actionId])
const initialValues = computed(() => action.value?.defaultValues())

// Only the page knows what it counts, so a pane without a label counts nothing rather
// than guessing a noun.
const subtitle = computed(() =>
  props.countsLabel?.(props.targets.length, monitoringService?.total.value ?? 0)
)

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
    :subtitle="showCount ? subtitle : undefined"
    :description="action.description"
    :submit-label="action.submitLabel"
    :form="action.form"
    :form-props="action.formProps"
    :initial-values="initialValues"
    :indent="indent"
    :show-close="showClose"
    @submit="onSubmit"
    @cancel="emit('cancel')"
  />
</template>
