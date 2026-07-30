<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkBadge from 'cmk-ui-library/components/CmkBadge.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { SIFormatter } from 'cmk-ui-library/lib/unit-format/notationFormatter'
import { computed } from 'vue'

import KpiSparkLine from '@/network-flow/CmkKpiStatCard/KpiSparkLine.vue'
import CmkRankedTable from '@/network-flow/CmkRankedTable'
import type { RankedTableColumn, RankedTableRow } from '@/network-flow/CmkRankedTable'
import { CHART_COLOR_CSS } from '@/network-flow/colors'

import type { ComputedNetworkFlowHost } from '../api/context'

const { _t } = usei18n()

const props = defineProps<{ data: ComputedNetworkFlowHost }>()

const host = computed<ComputedNetworkFlowHost>(() => props.data)

const byteFormatter = new SIFormatter('B', { type: 'strict', digits: 2 })

const stateBadge = computed<{ label: string; color: 'success' | 'warning' | 'danger' } | null>(
  () => {
    switch (host.value.state) {
      case 'up':
        return { label: _t('UP'), color: 'success' }
      case 'down':
        return { label: _t('DOWN'), color: 'danger' }
      case 'unreachable':
        return { label: _t('UNREACHABLE'), color: 'warning' }
      default:
        return null
    }
  }
)

// Only for unmonitored IPs; monitored hosts show the status badge instead.
const localityBadge = computed<string | null>(() => {
  if (host.value.hostname !== null || host.value.is_local === null) {
    return null
  }
  return host.value.is_local ? _t('Internal') : _t('Remote')
})

const applicationColumns = computed<RankedTableColumn[]>(() => [
  { key: 'protocol', title: _t('Application'), render: 'text', bar: false },
  { key: 'ingress', title: _t('In'), render: 'bytes', bar: false },
  { key: 'egress', title: _t('Out'), render: 'bytes', bar: false },
  { key: 'total', title: _t('Total'), render: 'bytes', bar: true }
])

const applicationRows = computed<RankedTableRow[]>(() =>
  host.value.applications.map((application) => ({
    protocol: application.protocol,
    ingress: application.ingress,
    egress: application.egress,
    total: application.total
  }))
)

const peerColumns = computed<RankedTableColumn[]>(() => [
  { key: 'host', title: _t('Peer'), render: 'text', bar: false },
  { key: 'volume', title: _t('Volume'), render: 'bytes', bar: true }
])

const peerRows = computed<RankedTableRow[]>(() =>
  host.value.peers.map((peer) => ({ host: peer.host, volume: peer.volume }))
)
</script>

<template>
  <div class="network-flow-host-slide-in-overview">
    <section class="network-flow-host-slide-in-overview__identity">
      <div class="network-flow-host-slide-in-overview__title-row">
        <CmkHeading type="h3">{{ host.hostname ?? host.ip }}</CmkHeading>
        <CmkBadge v-if="stateBadge" :color="stateBadge.color" size="small">
          {{ stateBadge.label }}
        </CmkBadge>
        <CmkBadge v-else-if="localityBadge" color="default" size="small">
          {{ localityBadge }}
        </CmkBadge>
      </div>
      <CmkParagraph
        v-if="host.hostname !== null"
        class="network-flow-host-slide-in-overview__subtitle"
      >
        {{ host.ip }}
      </CmkParagraph>
      <a
        v-if="host.service_page_url"
        class="network-flow-host-slide-in-overview__host-link"
        :href="host.service_page_url"
      >
        {{ _t('Open host in Checkmk') }}
      </a>
    </section>

    <section class="network-flow-host-slide-in-overview__traffic">
      <dl class="network-flow-host-slide-in-overview__metrics">
        <div>
          <dt>{{ _t('Ingress') }}</dt>
          <dd>{{ byteFormatter.render(host.ingress) }}</dd>
        </div>
        <div>
          <dt>{{ _t('Egress') }}</dt>
          <dd>{{ byteFormatter.render(host.egress) }}</dd>
        </div>
      </dl>
      <div class="network-flow-host-slide-in-overview__sparkline">
        <KpiSparkLine :series="host.series" :color="CHART_COLOR_CSS.green" />
      </div>
    </section>

    <section class="network-flow-host-slide-in-overview__table">
      <CmkHeading type="h4">{{ _t('Top applications') }}</CmkHeading>
      <CmkParagraph v-if="applicationRows.length === 0">
        {{ _t('No application traffic in the last 30 minutes.') }}
      </CmkParagraph>
      <CmkRankedTable
        v-else
        :columns="applicationColumns"
        :rows="applicationRows"
        bar-color="green"
      />
    </section>

    <section class="network-flow-host-slide-in-overview__table">
      <CmkHeading type="h4">{{ _t('Top peers') }}</CmkHeading>
      <CmkParagraph v-if="peerRows.length === 0">
        {{ _t('No peer traffic in the last 30 minutes.') }}
      </CmkParagraph>
      <CmkRankedTable v-else :columns="peerColumns" :rows="peerRows" bar-color="blue" />
    </section>
  </div>
</template>

<style scoped>
.network-flow-host-slide-in-overview {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-double);
}

.network-flow-host-slide-in-overview__title-row {
  display: flex;
  gap: var(--spacing);
  align-items: center;
}

.network-flow-host-slide-in-overview__subtitle {
  color: var(--color-mid-grey-50);
}

.network-flow-host-slide-in-overview__host-link {
  display: inline-block;
  margin-top: var(--spacing-half);
}

.network-flow-host-slide-in-overview__traffic {
  display: flex;
  gap: var(--spacing-double);
  align-items: center;
  justify-content: space-between;
}

.network-flow-host-slide-in-overview__metrics {
  display: flex;
  gap: var(--spacing-double);
  margin: 0;
}

.network-flow-host-slide-in-overview__metrics dt {
  font-size: 0.85em;
  color: var(--color-mid-grey-50);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.network-flow-host-slide-in-overview__metrics dd {
  margin: 0;
  font-size: 1.4em;
  font-variant-numeric: tabular-nums;
}

.network-flow-host-slide-in-overview__sparkline {
  flex: 1;
  max-width: 200px;
  height: 48px;
}

.network-flow-host-slide-in-overview__table {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
}
</style>
