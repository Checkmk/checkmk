<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkLink from '@/components/CmkLink.vue'
import CmkStateCountBar, { type StateSegment } from '@/components/CmkStateCountBar.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

import type { HostEntry, HostOverview } from '@/monitoring/shared/api/types'

import HostOverviewChips from './HostOverviewChips.vue'
import HostOverviewLabels from './HostOverviewLabels.vue'

// `host` carries the synchronously available list-row data (including the
// service counts); `data` is the detailed overview fetched by the slide-in
// framework and handed in via the `data` prop once its `load` promise settled.
const props = defineProps<{ host: HostEntry; data: HostOverview }>()

const { _t } = usei18n()

const serviceSegments = computed<StateSegment[]>(() => [
  { label: _t('OK'), count: props.host.num_services_ok, color: 'success' },
  { label: _t('WARN'), count: props.host.num_services_warn, color: 'warning' },
  { label: _t('CRIT'), count: props.host.num_services_crit, color: 'danger' },
  { label: _t('UNKNOWN'), count: props.host.num_services_unknown, color: 'unknown' },
  { label: _t('PENDING'), count: props.host.num_services_pending, color: 'default' }
])

const tagChips = computed(() =>
  Object.entries(props.data.tags).map(([group, tag]) => `${group}: ${tag}`)
)

function timeSince(iso: string): string {
  const seconds = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000))
  if (seconds < 60) {
    return _t('%{count} sec', { count: seconds })
  }
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) {
    return _t('%{count} min', { count: minutes })
  }
  const hours = Math.round(minutes / 60)
  if (hours < 24) {
    return _t('%{count} h', { count: hours })
  }
  return _t('%{count} d', { count: Math.round(hours / 24) })
}

function formatTimestamp(iso: string): string {
  const date = new Date(iso)
  const pad = (value: number): string => String(value).padStart(2, '0')
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ` +
    `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
  )
}
</script>

<template>
  <div class="monitoring-host-overview-tab">
    <div class="monitoring-host-overview-tab__status-link">
      <CmkLink :href="data.legacy_host_status_link" target="_top">
        {{ _t('Show full host status') }}
      </CmkLink>
    </div>

    <dl class="monitoring-host-overview-tab__grid">
      <dt>{{ _t('Host name') }}</dt>
      <dd>{{ data.name }}</dd>

      <dt>{{ _t('Host alias') }}</dt>
      <dd>{{ data.alias }}</dd>

      <dt>{{ _t('IP address') }}</dt>
      <dd>{{ data.address }}</dd>

      <dt>{{ _t('Folder') }}</dt>
      <dd>{{ data.folder ?? '—' }}</dd>
    </dl>

    <hr class="monitoring-host-overview-tab__divider" />

    <dl class="monitoring-host-overview-tab__grid monitoring-host-overview-tab__grid--chips">
      <dt>{{ _t('Site') }}</dt>
      <dd>{{ data.site_alias }}</dd>

      <dt>{{ _t('Site ID') }}</dt>
      <dd>{{ data.site_id }}</dd>

      <template v-if="data.customer !== null">
        <dt>{{ _t('Customer') }}</dt>
        <dd>{{ data.customer }}</dd>
      </template>

      <dt>{{ _t('Contact groups') }}</dt>
      <dd>
        <HostOverviewChips :items="data.contact_groups" />
      </dd>
    </dl>

    <hr class="monitoring-host-overview-tab__divider" />

    <dl class="monitoring-host-overview-tab__grid">
      <dt>{{ _t('Last check') }}</dt>
      <dd>{{ formatTimestamp(data.last_check) }}</dd>

      <dt>{{ _t('Age') }}</dt>
      <dd>{{ timeSince(data.last_state_change) }}</dd>
    </dl>

    <dl class="monitoring-host-overview-tab__grid monitoring-host-overview-tab__grid--chips">
      <dt>{{ _t('Tags') }}</dt>
      <dd>
        <HostOverviewChips :items="tagChips" />
      </dd>

      <dt>{{ _t('Labels') }}</dt>
      <dd>
        <HostOverviewLabels :labels="data.labels" />
      </dd>
    </dl>

    <section class="monitoring-host-overview-tab__section">
      <CmkHeading type="h3">{{ _t('Service summary') }}</CmkHeading>
      <CmkStateCountBar :segments="serviceSegments" />
    </section>
  </div>
</template>

<style scoped>
.monitoring-host-overview-tab {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-double);
}

.monitoring-host-overview-tab__status-link {
  position: absolute;
  top: 0;
  right: 0;
}

.monitoring-host-overview-tab__divider {
  width: 100%;
  height: 1px;
  margin: 0;
  border: 0;
  background: var(--ux-theme-4);
}

.monitoring-host-overview-tab__grid {
  display: grid;
  grid-template-columns: minmax(120px, max-content) 1fr;
  gap: var(--dimension-4) var(--spacing);
  margin: 0;
}

.monitoring-host-overview-tab__section,
.monitoring-host-overview-tab__relations {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

.monitoring-host-overview-tab__relations-empty {
  color: var(--font-color-dimmed);
}

.monitoring-host-overview-tab__grid dt {
  color: var(--font-color);
}

.monitoring-host-overview-tab__grid dd {
  margin: 0;
}

.monitoring-host-overview-tab__grid--chips {
  align-items: start;
}
</style>
