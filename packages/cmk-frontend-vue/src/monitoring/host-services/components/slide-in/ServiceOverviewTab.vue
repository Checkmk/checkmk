<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkCatalogPanel from 'cmk-ui-library/components/CmkCatalogPanel.vue'
import CmkIcon from 'cmk-ui-library/components/CmkIcon/CmkIcon.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { ServiceOverview } from '@/monitoring/shared/api/types'
import HostStateDisplay from '@/monitoring/shared/components/HostStateDisplay.vue'
import ModeIcons from '@/monitoring/shared/components/ModeIcons.vue'
import PluginOutput from '@/monitoring/shared/components/PluginOutput.vue'
import OverviewChips from '@/monitoring/shared/components/slide-in/OverviewChips.vue'
import OverviewDetailList from '@/monitoring/shared/components/slide-in/OverviewDetailList.vue'
import OverviewLabels from '@/monitoring/shared/components/slide-in/OverviewLabels.vue'
import { formatTimestamp } from '@/monitoring/shared/formatTimestamp'
import { toNameItems, toTagItems } from '@/monitoring/shared/labels'
import { useTimeSince } from '@/monitoring/shared/useTimeSince'

const props = defineProps<{ data: ServiceOverview }>()

const { _t } = usei18n()

const timeSince = useTimeSince()

const checkAttempt = computed(
  () => `${props.data.current_attempt}/${props.data.max_check_attempts}`
)

const tagChips = computed(() => toTagItems(props.data.tags))
const contactGroupChips = computed(() => toNameItems(props.data.contact_groups))

const lastCheck = computed(() =>
  props.data.last_check === null ? '–' : formatTimestamp(props.data.last_check)
)

const nextCheck = computed(() =>
  props.data.next_check === null ? '–' : formatTimestamp(props.data.next_check)
)
</script>

<template>
  <div class="monitoring-service-overview-tab">
    <OverviewDetailList align="start">
      <dt>{{ _t('Host:') }}</dt>
      <dd class="monitoring-service-overview-tab__host">
        <HostStateDisplay :state="data.host_state" />
        <ModeIcons v-if="data.host_modes.length" :modes="data.host_modes" />
        <span>{{ data.host_name }}</span>
        <a
          class="monitoring-service-overview-tab__host-link"
          :href="data.legacy_host_status_link"
          target="_top"
          :title="_t('Show details of host %{name}', { name: data.host_name })"
          :aria-label="_t('Show details of host %{name}', { name: data.host_name })"
        >
          <CmkIcon name="folder" size="small" />
        </a>
      </dd>

      <dt>{{ _t('Host alias:') }}</dt>
      <dd>{{ data.host_alias }}</dd>
    </OverviewDetailList>

    <hr class="monitoring-service-overview-tab__divider" />

    <OverviewDetailList align="start">
      <dt>{{ _t('Contact groups:') }}</dt>
      <dd>
        <OverviewChips :items="contactGroupChips" />
      </dd>

      <dt>{{ _t('Tags:') }}</dt>
      <dd>
        <OverviewChips :items="tagChips" />
      </dd>

      <dt>{{ _t('Labels:') }}</dt>
      <dd>
        <OverviewLabels :labels="data.labels" />
      </dd>
    </OverviewDetailList>

    <hr class="monitoring-service-overview-tab__divider" />

    <OverviewDetailList align="start">
      <dt>{{ _t('Last check:') }}</dt>
      <dd>{{ lastCheck }}</dd>

      <dt>{{ _t('State age:') }}</dt>
      <dd>{{ timeSince(data.last_state_change) }}</dd>

      <dt>{{ _t('Current check attempt:') }}</dt>
      <dd>{{ checkAttempt }}</dd>

      <dt>{{ _t('Time of next scheduled check:') }}</dt>
      <dd>{{ nextCheck }}</dd>
    </OverviewDetailList>

    <hr class="monitoring-service-overview-tab__divider" />

    <OverviewDetailList align="start">
      <dt>{{ _t('Service summary:') }}</dt>
      <dd><PluginOutput :output="data.summary" /></dd>
    </OverviewDetailList>

    <CmkCatalogPanel :title="_t('Service details')" :open="false">
      <pre v-if="data.long_output" class="monitoring-service-overview-tab__details-text">{{
        data.long_output
      }}</pre>
      <CmkParagraph v-else class="monitoring-service-overview-tab__details-empty">
        {{ _t('This check plugin reports no further details.') }}
      </CmkParagraph>
    </CmkCatalogPanel>
  </div>
</template>

<style scoped>
.monitoring-service-overview-tab {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-double);
}

.monitoring-service-overview-tab__divider {
  width: 100%;
  height: 1px;
  margin: 0;
  border: 0;
  background: var(--ux-theme-4);
}

.monitoring-service-overview-tab__host {
  display: flex;
  flex-flow: row wrap;
  gap: var(--dimension-3);
  align-items: center;
}

.monitoring-service-overview-tab__host-link {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  margin-left: auto;
}

.monitoring-service-overview-tab__details-empty {
  color: var(--font-color-dimmed);
}

.monitoring-service-overview-tab__details-text {
  margin: 0;
  overflow-x: auto;
  font-family: monospace;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
</style>
