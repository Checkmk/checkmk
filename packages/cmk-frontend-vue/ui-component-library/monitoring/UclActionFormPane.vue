<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type Options, type PanelConfig } from '@ucl/_ucl/components/detail-page'

import codeExample from './UclActionFormPaneCodeExample.vue?raw'

type FormKind = 'none' | 'comment' | 'reschedule' | 'schedule-downtime'

const FORM_OPTIONS: Options<FormKind>[] = [
  { title: 'No inputs (confirm)', name: 'none' },
  { title: 'Comment', name: 'comment' },
  { title: 'Reschedule', name: 'reschedule' },
  { title: 'Schedule downtime', name: 'schedule-downtime' }
]

export const panelConfig = {
  form: {
    type: 'list' as const,
    title: 'form',
    options: FORM_OPTIONS,
    initialState: 'comment' as FormKind,
    help: 'The form fragment rendered in the pane body. "No inputs" makes the action immediately submittable.'
  }
} satisfies PanelConfig
</script>

<script setup lang="ts">
import {
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout,
  UclPropertiesPanel
} from '@ucl/_ucl/components/detail-page'
import type { InferPanelState } from '@ucl/_ucl/types/prop-panel'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { type Component, computed, ref } from 'vue'

import { useRescheduleHostsAction } from '@/monitoring/all-hosts/actions/rescheduleHosts'
import { useScheduleHostDowntimeAction } from '@/monitoring/all-hosts/actions/scheduleHostDowntime'
import ActionFormPane from '@/monitoring/shared/components/action/ActionFormPane.vue'
import type { DowntimeRecurrenceOption } from '@/monitoring/shared/components/action/actions/ScheduleDowntimeForm.vue'
import { useCommentAction } from '@/monitoring/shared/components/action/actions/comment'
import type { MonitoringAction } from '@/monitoring/shared/components/action/types'

defineProps<{ screenshotMode: boolean }>()

/** What a site running the Micro Core offers to repeat a downtime on. */
const DOWNTIME_RECURRENCES: DowntimeRecurrenceOption[] = [
  { recur: 'fixed', title: 'never' },
  { recur: 'hour', title: 'hour' },
  { recur: 'day', title: 'day' },
  { recur: 'week', title: 'week' },
  { recur: 'day_of_month', title: 'same day of the month' }
]

const propState = ref(
  Object.fromEntries(
    Object.entries(panelConfig).map(([key, def]) => [key, def.initialState])
  ) as InferPanelState<typeof panelConfig>
)

const actions: Record<Exclude<FormKind, 'none'>, MonitoringAction> = {
  comment: useCommentAction(),
  reschedule: useRescheduleHostsAction(),
  'schedule-downtime': useScheduleHostDowntimeAction(DOWNTIME_RECURRENCES, '#')
}

const activeAction = computed<MonitoringAction | undefined>(() =>
  propState.value.form === 'none' ? undefined : actions[propState.value.form]
)
const title = computed<TranslatedString>(
  () => activeAction.value?.title ?? ('Run action' as TranslatedString)
)
const form = computed<Component | undefined>(() => activeAction.value?.form)
const initialValues = computed<unknown>(() => activeAction.value?.defaultValues() ?? {})

const lastResult = ref<string | null>(null)

function onSubmit(values: unknown): void {
  lastResult.value = JSON.stringify(values)
}

function onCancel(): void {
  lastResult.value = 'cancelled'
}
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>ActionFormPane</UclDetailPageHeader>

    <UclDetailPageComponent>
      <div class="ucl-action-form-pane__stack">
        <div class="ucl-action-form-pane__container">
          <ActionFormPane
            :key="propState.form"
            :title="title"
            :subtitle="'web-server-01' as TranslatedString"
            :form="form"
            :initial-values="initialValues"
            @submit="onSubmit"
            @cancel="onCancel"
          />
        </div>

        <p class="ucl-action-form-pane__hint">
          The pane is a generic shell: it renders the supplied <code>form</code> fragment over a
          draft and emits <code>submit</code> with its values. Last result:
          <strong>{{ lastResult ?? '—' }}</strong>
        </p>
      </div>

      <template #properties>
        <UclPropertiesPanel v-model="propState" :config="panelConfig" />
      </template>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />
  </UclDetailPageLayout>
</template>

<style scoped>
.ucl-action-form-pane__stack {
  display: flex;
  flex-direction: column;
  align-items: start;
  gap: var(--dimension-4);
  width: 100%;
}

.ucl-action-form-pane__container {
  width: 360px;
  max-width: 100%;
  height: 360px;
  border: 1px dashed var(--ux-theme-6);
  border-radius: 4px;
  box-sizing: border-box;
}

.ucl-action-form-pane__hint {
  margin: 0;
  font-style: italic;
  opacity: 0.7;
}
</style>
