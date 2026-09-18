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
import { computed, markRaw, onUnmounted, ref, watch } from 'vue'

import TableSkeleton from '@/loading-transition/TableSkeleton.vue'
import { HOST_TAB_OVERVIEW } from '@/monitoring/all-hosts/slideInTabs'
import EventHistoryApp from '@/monitoring/events/EventHistoryApp.vue'
import { fetchEvents } from '@/monitoring/events/api'
import { HostApi } from '@/monitoring/shared/api/hosts'
import type { HostEntry, HostOverview, HostRef } from '@/monitoring/shared/api/types'
import HostHeader, { type HostHeaderSubject } from '@/monitoring/shared/components/HostHeader.vue'
import ActionFeedback, {
  type ActionFeedback as ActionFeedbackResult
} from '@/monitoring/shared/components/action/ActionFeedback.vue'
import MonitoringActionPane from '@/monitoring/shared/components/action/MonitoringActionPane.vue'
import type { MonitoringActionRegistry } from '@/monitoring/shared/components/action/registry'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'
import SlideInActions from '@/monitoring/shared/components/slide-in/SlideInActions.vue'
import { ACTION_REFRESH_DELAY_MS } from '@/monitoring/shared/constants'
import { useSlideInActions } from '@/monitoring/shared/services/useSlideInActions'

import HostOverviewSkeleton from './slide-in/HostOverviewSkeleton.vue'
import HostOverviewTab from './slide-in/HostOverviewTab.vue'

const props = withDefaults(
  defineProps<{
    /** The host to detail. `null` keeps the slide-in closed. */
    host: HostEntry | null
    actions: MonitoringActionRegistry
    /** Row action buttons carrying the `{host}` placeholder, resolved here per host. */
    rowActions?: CellAction[]
    /** The actions the backend reports this user may run on a host. */
    permittedActions?: CellAction[]
    loadActionMenu: (host: HostRef) => Promise<CellAction[]>
    /** The tab on show, as a `v-model:activeTabId`; forwarded to the panel. */
    activeTabId?: string | undefined
    /** Counts how often the reader asked for the relations; 0 means they did not. */
    revealRelationsRequest?: number
  }>(),
  {
    rowActions: () => [],
    permittedActions: () => [],
    activeTabId: undefined
  }
)

const emit = defineEmits<{
  (event: 'close'): void
  (event: 'performed', result: ActionFeedbackResult): void
  (event: 'update:activeTabId', id: string): void
}>()

const { _t } = usei18n()

const hostApi = new HostApi()

const open = computed(() => props.host !== null)

const targets = computed<HostRef[]>(() =>
  props.host ? [{ site_id: props.host.site_id, name: props.host.name }] : []
)

// Only the actions the user may run and that this page actually implements reach the buttons.
const slideInActions = computed(() =>
  props.permittedActions.filter((action) => action.id in props.actions)
)

// The header outlives the tab body, so the loaded overview is kept here rather than only being
// handed to the tab component.
const overview = ref<HostOverview | null>(null)

watch(
  () => props.host,
  () => {
    overview.value = null
  }
)

async function loadOverview(host: HostRef): Promise<HostOverview> {
  const loaded = await hostApi.fetchHostOverview(host)
  // A request started for a host the user has since navigated away from must not win the race
  // against the one for the host now on screen.
  if (props.host?.site_id === host.site_id && props.host.name === host.name) {
    overview.value = loaded
  }
  return loaded
}

const displayHost = computed<HostHeaderSubject | null>(() => {
  if (!props.host) {
    return null
  }
  const loaded = overview.value
  if (!loaded) {
    return props.host
  }
  return {
    name: props.host.name,
    site_id: props.host.site_id,
    state: loaded.state,
    is_flapping: loaded.is_flapping,
    stale: loaded.stale,
    modes: loaded.modes
  }
})

const reloadToken = ref(0)

let reloadTimer: ReturnType<typeof setTimeout> | null = null

onUnmounted(() => {
  if (reloadTimer !== null) {
    clearTimeout(reloadTimer)
  }
})

function onActionPerformed(result: ActionFeedbackResult): void {
  // The header sits outside the tabbed body, so it needs its own reload - unless the Overview
  // tab is active (or none has been picked yet, which defaults to it), since reloadToken then
  // reloads it via this same loadOverview() already.
  if (result.variant === 'success' && props.host) {
    if (reloadTimer !== null) {
      clearTimeout(reloadTimer)
    }
    const siteId = props.host.site_id
    const name = props.host.name
    // Scheduling a downtime or acknowledging a problem sends an external command to the core
    // and returns before the core has necessarily applied it, so an immediate reload can still
    // show the pre-action state. Delayed like the table's own post-action refresh, for the same
    // reason.
    reloadTimer = setTimeout(() => {
      reloadTimer = null
      if (props.host?.site_id !== siteId || props.host.name !== name) {
        return
      }
      reloadToken.value++
      if (props.activeTabId !== undefined && props.activeTabId !== HOST_TAB_OVERVIEW) {
        loadOverview({ site_id: siteId, name }).catch(() => {})
      }
    }, ACTION_REFRESH_DELAY_MS)
  }
  emit('performed', result)
}

const {
  activeActionId,
  runningActionId,
  feedback,
  feedbackOpen,
  openAction,
  closeAction,
  applyFeedback,
  perform
} = useSlideInActions<HostRef>(
  () => props.actions,
  targets,
  () => props.host,
  onActionPerformed
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
      id: HOST_TAB_OVERVIEW,
      title: _t('Overview'),
      component: markRaw(HostOverviewTab),
      skeleton: markRaw(HostOverviewSkeleton),
      props: { revealRelationsRequest: props.revealRelationsRequest },
      load: () => loadOverview({ site_id: host.site_id, name: host.name })
    },
    {
      id: 'history',
      title: _t('History'),
      component: markRaw(EventHistoryApp),
      skeleton: markRaw(TableSkeleton),
      props: { subject: 'host' },
      load: () => fetchEvents({ site_id: host.site_id, name: host.name })
    }
  ]
})

async function onCommand(payload: { id: string; host: HostRef }): Promise<void> {
  await perform(payload.id, [payload.host])
}
</script>

<template>
  <!--
    Keyed on the host, so picking another row while the panel is open remounts the tabs:
    CmkSlideInTabbed only drops its cached tab data when `open` flips, which never happens here -
    AllHostsApp reassigns the host without closing the panel first.
  -->
  <CmkSlideInTabbed
    :key="host ? `${host.site_id}/${host.name}` : ''"
    :open="open"
    :tabs="tabs"
    :reload-token="reloadToken"
    :active-tab-id="activeTabId"
    :override-active="activeActionId !== null"
    :header="{ title: _t('Host details'), closeButton: true }"
    @close="emit('close')"
    @update:active-tab-id="emit('update:activeTabId', $event)"
  >
    <template #above-tabs>
      <HostHeader
        v-if="displayHost"
        :host="displayHost"
        :actions="inlineActions"
        :load-action-menu="actionMenuLoader"
        @command="onCommand"
      />
    </template>
    <template v-if="slideInActions.length" #actions>
      <SlideInActions
        :actions="slideInActions"
        :running-action-id="runningActionId"
        @select="openAction"
      />
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
        @feedback="applyFeedback"
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
