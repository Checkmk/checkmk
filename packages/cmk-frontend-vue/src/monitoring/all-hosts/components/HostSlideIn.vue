<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton/CmkButton.vue'
import CmkIcon from 'cmk-ui-library/components/CmkIcon/CmkIcon.vue'
import CmkSlideInTabbed, { type SlideInTab } from 'cmk-ui-library/components/CmkSlideInTabbed'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, markRaw, ref, watch } from 'vue'

import { HostApi } from '@/monitoring/all-hosts/api/hosts'
import type { HostEntry, HostRef } from '@/monitoring/shared/api/types'
import ActionFeedback, {
  type ActionFeedback as ActionFeedbackResult
} from '@/monitoring/shared/components/action/ActionFeedback.vue'
import MonitoringActionPane from '@/monitoring/shared/components/action/MonitoringActionPane.vue'
import { RESCHEDULE_ACTION_ID } from '@/monitoring/shared/components/action/actions/reschedule'
import type { MonitoringActionRegistry } from '@/monitoring/shared/components/action/registry'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'

import HostOverviewSkeleton from './slide-in/HostOverviewSkeleton.vue'
import HostOverviewTab from './slide-in/HostOverviewTab.vue'
import HostSlideInActions from './slide-in/HostSlideInActions.vue'
import HostSlideInHeader from './slide-in/HostSlideInHeader.vue'

const props = withDefaults(
  defineProps<{
    /** The host to detail. `null` keeps the slide-in closed. */
    host: HostEntry | null
    actions: MonitoringActionRegistry
    /** Row action buttons carrying the `{host}` placeholder, resolved here per host. */
    rowActions?: CellAction[]
    loadActionMenu: (host: HostRef) => Promise<CellAction[]>
  }>(),
  { rowActions: () => [] }
)

const emit = defineEmits<{
  (event: 'close'): void
  (event: 'performed', result: ActionFeedbackResult): void
}>()

const { _t } = usei18n()

const hostApi = new HostApi()

const activeActionId = ref<string | null>(null)
const runningActionId = ref<string | null>(null)
const feedback = ref<ActionFeedbackResult | null>(null)
const feedbackOpen = ref(false)

const open = computed(() => props.host !== null)

const targets = computed<HostRef[]>(() =>
  props.host ? [{ site_id: props.host.site_id, name: props.host.name }] : []
)

const inlineActions = computed<CellAction[]>(() => {
  const host = props.host
  if (!host) {
    return []
  }
  const name = host.name
  const statusAction: CellAction = {
    id: 'show_status',
    label: _t('Show status of host %{name}', { name }),
    icon: 'folder',
    url: host.legacy_host_status_link
  }
  const resolved = props.rowActions.map((action) => ({
    ...action,
    label: action.id === 'edit' ? _t('Edit host %{name}', { name }) : action.label,
    url: action.url?.replace('{host}', encodeURIComponent(name))
  }))
  return [statusAction, ...resolved]
})

const actionMenuLoader = computed<(() => Promise<CellAction[]>) | undefined>(() => {
  const host = props.host
  if (!host) {
    return undefined
  }
  const hostRef: HostRef = { site_id: host.site_id, name: host.name }
  return () => props.loadActionMenu(hostRef)
})

const tabs = computed<SlideInTab[]>(() => {
  const host = props.host
  if (!host) {
    return []
  }
  return [
    {
      id: 'overview',
      title: _t('Overview'),
      component: markRaw(HostOverviewTab),
      skeleton: markRaw(HostOverviewSkeleton),
      load: () => hostApi.fetchHostOverview({ site_id: host.site_id, name: host.name })
    }
  ]
})

watch(
  () => props.host,
  () => {
    activeActionId.value = null
    runningActionId.value = null
    feedback.value = null
  }
)

async function openAction(actionId: string): Promise<void> {
  if (!(actionId in props.actions)) {
    return
  }
  if (actionId === RESCHEDULE_ACTION_ID) {
    await performImmediately(actionId)
    return
  }
  feedback.value = null
  activeActionId.value = actionId
}

async function performImmediately(actionId: string): Promise<void> {
  const action = props.actions[actionId]
  if (!action || targets.value.length === 0) {
    return
  }
  runningActionId.value = actionId
  try {
    onFeedback(await action.perform(targets.value, action.defaultValues()))
  } finally {
    runningActionId.value = null
  }
}

function closeAction(): void {
  activeActionId.value = null
}

function onFeedback(result: ActionFeedbackResult): void {
  feedback.value = result
  feedbackOpen.value = true
  activeActionId.value = null
  emit('performed', result)
}

async function onCommand(payload: { id: string; host: HostRef }): Promise<void> {
  const action = props.actions[payload.id]
  if (!action) {
    return
  }
  onFeedback(await action.perform([payload.host], action.defaultValues()))
}
</script>

<template>
  <CmkSlideInTabbed
    :open="open"
    :tabs="tabs"
    :override-active="activeActionId !== null"
    :header="{ title: _t('Host details'), closeButton: true }"
    @close="emit('close')"
  >
    <template #above-tabs>
      <HostSlideInHeader
        v-if="host"
        :host="host"
        :actions="inlineActions"
        :load-action-menu="actionMenuLoader"
        @command="onCommand"
      />
    </template>
    <template #actions>
      <HostSlideInActions :running-action-id="runningActionId" @select="openAction" />
      <ActionFeedback
        v-if="feedback"
        v-model:open="feedbackOpen"
        class="monitoring-host-slide-in__feedback"
        :feedback="feedback"
      />
    </template>
    <template #override>
      <CmkButton variant="optional" class="monitoring-host-slide-in__back" @click="closeAction">
        <CmkIcon name="back" size="small" />
        {{ _t('Back to host detail view') }}
      </CmkButton>
      <MonitoringActionPane
        v-if="activeActionId"
        :action-id="activeActionId"
        :actions="actions"
        :targets="targets"
        indent
        :show-count="false"
        @cancel="closeAction"
        @feedback="onFeedback"
      />
    </template>
  </CmkSlideInTabbed>
</template>

<style scoped>
.monitoring-host-slide-in__feedback {
  margin-top: var(--spacing);
}

.monitoring-host-slide-in__back {
  gap: var(--dimension-3);
  margin-bottom: var(--spacing);
}
</style>
