<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, watch } from 'vue'

import HostSlideIn from '@/monitoring/shared/components/HostSlideIn.vue'
import type { ActionOutcome } from '@/monitoring/shared/components/action/types'
import type { DisplayOptions } from '@/monitoring/shared/types'
import { useHostActions } from '@/monitoring/shared/useHostActions'
import { useHostSlideInTabs } from '@/monitoring/shared/useHostSlideInTabs'

import type { HostsTableSubject, MonitoringTableActionOffer } from './tableDescriptors'

const props = defineProps<{
  subject: HostsTableSubject | null
  offer: MonitoringTableActionOffer | undefined
  displayOptions: DisplayOptions
}>()

const emit = defineEmits<{
  close: []
  performed: [outcome: ActionOutcome]
}>()

const hostActions = computed(() => useHostActions(props.offer ?? {}))

const tabs = useHostSlideInTabs()
const tabId = tabs.tabId
const revealRelationsRequest = tabs.revealRelationsRequest

watch(
  () => props.subject,
  (subject) => tabs.open(subject?.revealRelations ?? false)
)
</script>

<template>
  <HostSlideIn
    :host="subject?.host ?? null"
    :active-tab-id="tabId"
    :reveal-relations-request="revealRelationsRequest"
    :display-options="displayOptions"
    :actions="hostActions.registry"
    :row-actions="hostActions.rowActions"
    :permitted-actions="hostActions.permittedActions"
    :load-action-menu="hostActions.loadActionMenu"
    @update:active-tab-id="tabs.selectTab"
    @close="emit('close')"
    @performed="emit('performed', $event)"
  />
</template>
