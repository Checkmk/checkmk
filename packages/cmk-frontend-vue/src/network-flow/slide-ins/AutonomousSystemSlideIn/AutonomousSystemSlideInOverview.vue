<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { SIFormatter } from 'cmk-ui-library/lib/unit-format/notationFormatter'
import { computed } from 'vue'

import KpiSparkLine from '@/dashboard/components/CmkKpiStatCard/KpiSparkLine.vue'
import CmkRankedTable from '@/dashboard/components/CmkRankedTable'
import type { RankedTableColumn, RankedTableRow } from '@/dashboard/components/CmkRankedTable'
import { CHART_COLOR_CSS } from '@/network-flow/colors'

import type { ComputedNetworkFlowAutonomousSystem } from '../api/context'

const { _t } = usei18n()

const props = defineProps<{ data: ComputedNetworkFlowAutonomousSystem }>()

const autonomousSystem = computed<ComputedNetworkFlowAutonomousSystem>(() => props.data)

const throughputFormatter = new SIFormatter('bit/s', { type: 'strict', digits: 2 })

const applicationColumns = computed<RankedTableColumn[]>(() => [
  { key: 'protocol', title: _t('Application'), render: 'text', bar: false },
  { key: 'volume', title: _t('Volume'), render: 'bytes', bar: true }
])

const applicationRows = computed<RankedTableRow[]>(() =>
  autonomousSystem.value.applications.map((application) => ({
    protocol: application.protocol,
    volume: application.volume
  }))
)

const localHostColumns = computed<RankedTableColumn[]>(() => [
  { key: 'host', title: _t('Local host'), render: 'text', bar: false },
  { key: 'volume', title: _t('Volume'), render: 'bytes', bar: true }
])

const localHostRows = computed<RankedTableRow[]>(() =>
  autonomousSystem.value.local_hosts.map((host) => ({ host: host.host, volume: host.volume }))
)
</script>

<template>
  <div class="network-flow-autonomous-system-slide-in-overview">
    <section class="network-flow-autonomous-system-slide-in-overview__traffic">
      <dl class="network-flow-autonomous-system-slide-in-overview__metrics">
        <div>
          <dt>{{ _t('Throughput') }}</dt>
          <dd>{{ throughputFormatter.render(autonomousSystem.throughput) }}</dd>
        </div>
        <div>
          <dt>{{ _t('Active flows') }}</dt>
          <dd>{{ autonomousSystem.active_flows }}</dd>
        </div>
      </dl>
      <div class="network-flow-autonomous-system-slide-in-overview__sparkline">
        <KpiSparkLine :series="autonomousSystem.series" :color="CHART_COLOR_CSS.green" />
      </div>
    </section>

    <dl class="network-flow-autonomous-system-slide-in-overview__seen">
      <div>
        <dt>{{ _t('First seen') }}</dt>
        <dd>{{ autonomousSystem.first_seen || '—' }}</dd>
      </div>
      <div>
        <dt>{{ _t('Last seen') }}</dt>
        <dd>{{ autonomousSystem.last_seen || '—' }}</dd>
      </div>
    </dl>

    <section class="network-flow-autonomous-system-slide-in-overview__table">
      <CmkHeading type="h4">{{ _t('Top local hosts') }}</CmkHeading>
      <CmkParagraph v-if="localHostRows.length === 0">
        {{ _t('No traffic in the last 30 minutes.') }}
      </CmkParagraph>
      <CmkRankedTable
        v-else
        :columns="localHostColumns"
        :rows="localHostRows"
        :bar-color="CHART_COLOR_CSS.blue"
      />
    </section>

    <section class="network-flow-autonomous-system-slide-in-overview__table">
      <CmkHeading type="h4">{{ _t('Top applications') }}</CmkHeading>
      <CmkParagraph v-if="applicationRows.length === 0">
        {{ _t('No application traffic in the last 30 minutes.') }}
      </CmkParagraph>
      <CmkRankedTable
        v-else
        :columns="applicationColumns"
        :rows="applicationRows"
        :bar-color="CHART_COLOR_CSS.green"
      />
    </section>
  </div>
</template>

<style scoped>
.network-flow-autonomous-system-slide-in-overview {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-double);
}

.network-flow-autonomous-system-slide-in-overview__traffic {
  display: flex;
  gap: var(--spacing-double);
  align-items: center;
  justify-content: space-between;
}

.network-flow-autonomous-system-slide-in-overview__metrics,
.network-flow-autonomous-system-slide-in-overview__seen {
  display: flex;
  gap: var(--spacing-double);
  margin: 0;
}

.network-flow-autonomous-system-slide-in-overview__metrics dt,
.network-flow-autonomous-system-slide-in-overview__seen dt {
  font-size: 0.85em;
  color: var(--color-mid-grey-50);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.network-flow-autonomous-system-slide-in-overview__metrics dd {
  margin: 0;
  font-size: 1.4em;
  font-variant-numeric: tabular-nums;
}

.network-flow-autonomous-system-slide-in-overview__seen dd {
  margin: 0;
  font-variant-numeric: tabular-nums;
}

.network-flow-autonomous-system-slide-in-overview__sparkline {
  flex: 1;
  max-width: 200px;
  height: 48px;
}

.network-flow-autonomous-system-slide-in-overview__table {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
}
</style>
