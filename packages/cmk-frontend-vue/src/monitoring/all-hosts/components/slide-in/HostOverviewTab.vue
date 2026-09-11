<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { HostOverview, HostRef } from '@/monitoring/shared/api/types'
import ServiceSummaryBar from '@/monitoring/shared/components/ServiceSummaryBar.vue'
import OverviewChips from '@/monitoring/shared/components/slide-in/OverviewChips.vue'
import OverviewDetailList from '@/monitoring/shared/components/slide-in/OverviewDetailList.vue'
import OverviewLabels from '@/monitoring/shared/components/slide-in/OverviewLabels.vue'
import { formatTimestamp } from '@/monitoring/shared/formatTimestamp'
import { toNameItems, toTagItems } from '@/monitoring/shared/labels'
import { useTimeSince } from '@/monitoring/shared/useTimeSince'

import HostRelationsSection from './HostRelationsSection.vue'

const props = withDefaults(
  defineProps<{
    data: HostOverview
    /** Counts how often the reader asked for the relations; 0 means they did not. */
    revealRelationsRequest?: number
  }>(),
  { revealRelationsRequest: 0 }
)

const { _t } = usei18n()

const hostRef = computed<HostRef>(() => ({ site_id: props.data.site_id, name: props.data.name }))

const tagChips = computed(() => toTagItems(props.data.tags))
const contactGroupChips = computed(() => toNameItems(props.data.contact_groups))

const timeSince = useTimeSince()
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
        <OverviewChips :items="contactGroupChips" />
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
        <OverviewLabels :labels="data.labels" />
      </dd>
    </OverviewDetailList>

    <section class="monitoring-host-overview-tab__section">
      <CmkHeading type="h3">{{ _t('Service summary') }}</CmkHeading>
      <ServiceSummaryBar :counts="data.service_counts" :host="hostRef" />
    </section>
    <HostRelationsSection
      :relations="data.relations"
      :more-relations="data.more_relations"
      :reveal-request="revealRelationsRequest"
    />
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

.monitoring-host-overview-tab__section {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}
</style>
