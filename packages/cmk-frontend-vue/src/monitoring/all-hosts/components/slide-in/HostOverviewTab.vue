<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkStateCountBar, { type StateSegment } from 'cmk-ui-library/components/CmkStateCountBar.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { HostOverview } from '@/monitoring/shared/api/types'
import OverviewChips from '@/monitoring/shared/components/slide-in/OverviewChips.vue'
import OverviewDetailList from '@/monitoring/shared/components/slide-in/OverviewDetailList.vue'
import { formatTimestamp } from '@/monitoring/shared/formatTimestamp'

import HostOverviewLabels from './HostOverviewLabels.vue'

const props = defineProps<{ data: HostOverview }>()

const { _t } = usei18n()

const serviceSegments = computed<StateSegment[]>(() => [
  { label: _t('OK'), count: props.data.service_counts.ok, color: 'success' },
  { label: _t('WARN'), count: props.data.service_counts.warn, color: 'warning' },
  { label: _t('CRIT'), count: props.data.service_counts.crit, color: 'danger' },
  { label: _t('UNKNOWN'), count: props.data.service_counts.unknown, color: 'unknown' },
  { label: _t('PENDING'), count: props.data.service_counts.pending, color: 'default' }
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
</script>

<template>
  <div class="monitoring-host-overview-tab">
    <OverviewDetailList>
      <dt>{{ _t('Host name') }}</dt>
      <dd>{{ data.name }}</dd>

      <dt>{{ _t('Host alias') }}</dt>
      <dd>{{ data.alias }}</dd>

      <dt>{{ _t('IP address') }}</dt>
      <dd>{{ data.address }}</dd>

      <dt>{{ _t('Folder') }}</dt>
      <dd>{{ data.folder ?? '—' }}</dd>
    </OverviewDetailList>

    <hr class="monitoring-host-overview-tab__divider" />

    <OverviewDetailList align="start">
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
        <OverviewChips :items="data.contact_groups" />
      </dd>
    </OverviewDetailList>

    <hr class="monitoring-host-overview-tab__divider" />

    <OverviewDetailList>
      <dt>{{ _t('Last check') }}</dt>
      <dd>{{ formatTimestamp(data.last_check) }}</dd>

      <dt>{{ _t('Age') }}</dt>
      <dd>{{ timeSince(data.last_state_change) }}</dd>
    </OverviewDetailList>

    <OverviewDetailList align="start">
      <dt>{{ _t('Tags') }}</dt>
      <dd>
        <OverviewChips :items="tagChips" />
      </dd>

      <dt>{{ _t('Labels') }}</dt>
      <dd>
        <HostOverviewLabels :labels="data.labels" />
      </dd>
    </OverviewDetailList>

    <section class="monitoring-host-overview-tab__section">
      <CmkHeading type="h3">{{ _t('Service summary') }}</CmkHeading>
      <CmkStateCountBar :segments="serviceSegments" />
    </section>
    <section class="monitoring-host-overview-tab__relations">
      <CmkHeading type="h3">{{ _t('Relations') }}</CmkHeading>
      <CmkParagraph class="monitoring-host-overview-tab__relations-empty">
        {{ _t('No relations set') }}
      </CmkParagraph>
    </section>
  </div>
</template>

<style scoped>
.monitoring-host-overview-tab {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-double);
}

.monitoring-host-overview-tab__divider {
  width: 100%;
  height: 1px;
  margin: 0;
  border: 0;
  background: var(--ux-theme-4);
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
</style>
