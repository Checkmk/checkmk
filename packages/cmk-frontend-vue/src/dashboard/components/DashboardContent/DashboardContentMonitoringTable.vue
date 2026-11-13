<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, inject, watch } from 'vue'

import { useInjectCmkToken } from '@/dashboard/composables/useCmkToken'
import { useInjectIsPublicDashboard } from '@/dashboard/composables/useIsPublicDashboard'
import { useWidgetData } from '@/dashboard/composables/useWidgetData'
import { useWidgetSource } from '@/dashboard/composables/useWidgetSource'
import type { ComputedMonitoringTable, MonitoringTableContent } from '@/dashboard/types/widget'
import { dashboardAPI } from '@/dashboard/utils'
import type { ActionOutcome } from '@/monitoring/shared/components/action/types'
import { ACTION_REFRESH_DELAY_MS } from '@/monitoring/shared/constants'
import { ACTION_FEEDBACK_STACK } from '@/monitoring/shared/services/useActionFeedbackStack'
import { unreachableSitesHint } from '@/monitoring/shared/unreachableSites'
import MonitoringTableWidget from '@/monitoring/table-widget/MonitoringTableWidget.vue'
import { WidgetTableState } from '@/monitoring/table-widget/WidgetTableState'
import { monitoringTableRegistry } from '@/monitoring/table-widget/registry'
import type {
  MonitoringTableActions,
  MonitoringTableDescriptor
} from '@/monitoring/table-widget/tableDescriptors'

import WidgetFigureFrame from './figures/WidgetFigureFrame.vue'
import type { ContentProps } from './types'

const props = defineProps<ContentProps<MonitoringTableContent>>()
const { _t } = usei18n()

const { source, headers } = useWidgetSource(props)
const tableState = new WidgetTableState(props.content.sort)
watch([() => props.content.sort.join(','), () => props.content.columns.join(',')], () =>
  tableState.reset(props.content.sort)
)
// The backend computes the rows of the very table the descriptor is looked up for.
const descriptor = computed(
  () =>
    monitoringTableRegistry.descriptor(props.content.table) as MonitoringTableDescriptor<
      ComputedMonitoringTable['rows'][number]
    >
)

const { state, retry, refresh } = useWidgetData<ComputedMonitoringTable>(
  () =>
    dashboardAPI.computeMonitoringTable(
      { source: source.value, sort: tableState.encodedSort() },
      headers
    ),
  () => [props.content, props.effective_filter_context, tableState.sortState.value],
  () => props.tick
)

// A successful action has taken effect - a rescheduled check has run - so the rows show it. They
// are read a moment later, as the pages read theirs: a service whose check is a byproduct of the
// host's "Check_MK" service gets its result only after that service has run. A table gone while
// its command ran - e.g. a refresh failed meanwhile - hands on no outcome: the dashboard still
// tells it, and the rows catch up on the next refresh.
function onPerformed(outcome: ActionOutcome): void {
  if (outcome.variant === 'success') {
    refresh(ACTION_REFRESH_DELAY_MS)
  }
}

// The wizard preview shows what the table will be, and a shared dashboard reaches no endpoint
// that runs an action: neither offers the rows' actions.
const offersRowActions = !props.isPreview && useInjectCmkToken() === undefined

// The dashboard tells how the commands picked in the rows go. Rendered on no dashboard, the rows
// offer no actions.
const feedback = inject(ACTION_FEEDBACK_STACK, null)

// A refresh offering the same actions keeps the previous offer, and so the rows' actions as built.
const actions = computed<MonitoringTableActions | undefined>((previous) => {
  const current = state.value
  if (
    !offersRowActions ||
    feedback === null ||
    props.content.read_only ||
    current.kind !== 'data'
  ) {
    return undefined
  }
  const offer = {
    actions: current.value.actions,
    links: current.value.links,
    host_actions: current.value.host_actions,
    host_links: current.value.host_links
  }
  return JSON.stringify(offer) === JSON.stringify(previous?.offer) ? previous : { offer, feedback }
})

function unappliedHint(value: ComputedMonitoringTable): string {
  return _t('Some filters not supported yet: %{filters}', {
    filters: value.unapplied_filters.map((filter) => filter.title).join(', ')
  })
}

// The wizard preview has no click shield, so that it scrolls, and the viewer of a shared
// dashboard cannot open the pages the rows link to: in neither may the links navigate away.
const blocksLinks = props.isPreview || useInjectIsPublicDashboard()

const readOnly = computed(() => !offersRowActions || blocksLinks || props.content.read_only)

function blockLinks(event: MouseEvent): void {
  if (blocksLinks && event.target instanceof Element && event.target.closest('a')) {
    event.preventDefault()
  }
}

function truncatedHint(value: ComputedMonitoringTable): string {
  return descriptor.value.truncatedHint(value.rows.length, value.matched)
}
</script>

<template>
  <WidgetFigureFrame
    :effective-title="effectiveTitle"
    :general_settings="general_settings"
    :state="state"
    @retry="retry"
  >
    <template #default="{ value }">
      <div
        class="db-content-monitoring-table"
        @click.capture="blockLinks"
        @auxclick.capture="blockLinks"
      >
        <CmkAlert
          v-if="value.unreachable_sites.length > 0"
          class="db-content-monitoring-table__unreachable"
          variant="warning"
          :text="unreachableSitesHint(value.unreachable_sites)"
        />
        <p
          v-if="value.unapplied_filters.length > 0"
          class="db-content-monitoring-table__unapplied"
          role="note"
        >
          {{ unappliedHint(value) }}
        </p>
        <MonitoringTableWidget
          :descriptor="descriptor"
          :column-ids="content.columns"
          :rows="value.rows"
          :table-state="tableState"
          :display-options="{
            dateFormat: content.date_format,
            timestampFormat: content.timestamp_format
          }"
          :actions="actions"
          :read-only="readOnly"
          @performed="onPerformed"
        />
        <p v-if="value.matched > value.rows.length" class="db-content-monitoring-table__truncated">
          {{ truncatedHint(value) }}
        </p>
      </div>
    </template>
  </WidgetFigureFrame>
</template>

<style scoped>
.db-content-monitoring-table {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.db-content-monitoring-table__unreachable,
.db-content-monitoring-table__unapplied {
  margin: 0 0 var(--dimension-3);
}

.db-content-monitoring-table__unapplied {
  color: var(--font-color-dimmed);
}

.db-content-monitoring-table__truncated {
  margin: var(--dimension-3) 0 0;
  color: var(--font-color-dimmed);
}
</style>
