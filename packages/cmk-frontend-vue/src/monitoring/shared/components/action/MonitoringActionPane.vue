<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts" generic="Target">
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed, inject, onBeforeUnmount, provide, ref } from 'vue'

import { MONITORING_SERVICE } from '@/monitoring/shared/components/MonitoringTableContext'

import ActionFormPane from './ActionFormPane.vue'
import type { MonitoringActionRegistry } from './registry'
import { ACTION_TARGET_COUNT, type ActionOutcome } from './types'

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
  (event: 'feedback', result: ActionOutcome): void
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

// A pane that closes - the user closed the slide-in it sits in, or picked another action - no
// longer waits for what it ran.
const closed = new AbortController()
onBeforeUnmount(() => closed.abort())

// A command may take a while - a reschedule waits for its check - and the pane shows it runs.
const running = ref(false)

async function onSubmit(values: unknown): Promise<void> {
  const current = action.value
  if (!current || running.value) {
    return
  }
  running.value = true
  try {
    emit('feedback', await current.perform(props.targets, values, closed.signal))
  } finally {
    running.value = false
  }
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
    :running="running"
    @submit="onSubmit"
    @cancel="emit('cancel')"
  />
</template>
