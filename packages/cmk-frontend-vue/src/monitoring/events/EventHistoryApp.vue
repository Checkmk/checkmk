<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon/CmkIcon.vue'
import CmkLink from 'cmk-ui-library/components/CmkLink.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { MonitoringIcon } from '@/monitoring/shared/api/types'
import MonitoringTable from '@/monitoring/shared/components/MonitoringTable.vue'
import IconCell from '@/monitoring/shared/components/cell/IconCell.vue'
import StringCell from '@/monitoring/shared/components/cell/StringCell.vue'
import { formatTimestamp } from '@/monitoring/shared/formatTimestamp'

import type { EventEntry, EventsResponse } from './api'
import { type HistorySubject, buildHistoryColumns } from './historyColumns'

/**
 * The History tab of a monitoring slide-in: the events of one host (including those of
 * its services) or of one service, newest first.
 *
 * Written once for both slide-ins and parametrised by `subject`, which is static and
 * therefore arrives through `SlideInTab.props` rather than through the loaded `data`.
 * Both feed it the same endpoint's response (`fetchEvents`); the service side merely
 * narrows the query to its service. Loading, the skeleton and the retryable error state
 * all belong to `CmkSlideInTabbed`, which is why none of them appears here.
 */
const props = withDefaults(
  defineProps<{
    data: EventsResponse
    subject?: HistorySubject
  }>(),
  { subject: 'host' }
)

const { _t } = usei18n()

const SECONDS_PER_DAY = 24 * 60 * 60

const columns = computed(() => buildHistoryColumns(props.subject))

// The window's length is not part of the response, only its start; the difference to now
// re-derives the days the endpoint was asked for.
const windowDays = computed(() =>
  Math.round((Date.now() / 1000 - props.data.meta.since) / SECONDS_PER_DAY)
)

const emptyExplanation = computed(() =>
  props.subject === 'host'
    ? _t('This host and its services have no events in the last %{days} days.', {
        days: windowDays.value
      })
    : _t('This service has no events in the last %{days} days.', { days: windowDays.value })
)

// The time column carries the date, which is what lets the list stay flat instead of
// grouping its rows per day the way the legacy history views do.
function timeOf(event: EventEntry): string {
  return formatTimestamp(event.time)
}

// The event icon links nowhere: the History tab is read-only, and IconCell renders a
// link-less icon as a plain one.
function iconsOf(event: EventEntry): MonitoringIcon[] {
  return event.icon ? [event.icon] : []
}
</script>

<template>
  <div class="monitoring-event-history-app">
    <CmkLink
      class="monitoring-event-history-app__link"
      :href="data.meta.legacy_events_link"
      target="_top"
    >
      <CmkIcon name="history" size="small" />
      {{ _t('Open the full history view') }}
    </CmkLink>

    <CmkParagraph v-if="data.events.length === 0" class="monitoring-event-history-app__empty">
      {{ emptyExplanation }}
    </CmkParagraph>

    <template v-else>
      <MonitoringTable
        class="monitoring-event-history-app__table"
        :rows="data.events"
        :columns="columns"
        fetch-state="idle"
        :has-loaded="true"
        :filter-state="[]"
      >
        <template #row="{ row }">
          <IconCell column-id="icon" :icons="iconsOf(row)" />
          <StringCell column-id="time" :value="timeOf(row)" no-wrap />
          <StringCell column-id="event" :value="row.event" />
          <StringCell
            v-if="subject === 'host'"
            column-id="service_name"
            :value="row.service_name ?? undefined"
            :empty-label="_t('Host')"
          />
          <StringCell column-id="state_info" :value="row.state_info" />
          <StringCell column-id="plugin_output" :value="row.plugin_output" state-markers />
        </template>
      </MonitoringTable>

      <CmkParagraph v-if="data.meta.truncated" class="monitoring-event-history-app__truncated">
        {{
          _t('Only the %{limit} most recent events are shown. Open the full history for more.', {
            limit: data.meta.limit
          })
        }}
      </CmkParagraph>
    </template>
  </div>
</template>

<style scoped>
.monitoring-event-history-app {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
}

.monitoring-event-history-app__link {
  align-self: flex-end;
  align-items: center;
  width: auto;
}

.monitoring-event-history-app__empty,
.monitoring-event-history-app__truncated {
  color: var(--font-color-dimmed);
}

/*
 * MonitoringTable scrolls its own wrapper and virtualizes off it. Inside the slide-in the
 * scrolling ancestor is the panel's CmkScrollContainer, not a bounded flex column, so
 * without a height of its own the wrapper would grow and never scroll - and the
 * virtualizer would never see a viewport to window against. Bound it here.
 */
.monitoring-event-history-app__table {
  max-height: 60vh;
}
</style>
