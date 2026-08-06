<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkLink from 'cmk-ui-library/components/CmkLink.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import type { ServiceOverview } from '@/monitoring/shared/api/types'
import HostStateDisplay from '@/monitoring/shared/components/HostStateDisplay.vue'
import OverviewDetailList from '@/monitoring/shared/components/slide-in/OverviewDetailList.vue'

defineProps<{ data: ServiceOverview }>()

const { _t } = usei18n()
</script>

<template>
  <div class="monitoring-service-overview-tab">
    <OverviewDetailList align="start">
      <dt>{{ _t('Host name') }}</dt>
      <dd>{{ data.host_name }}</dd>

      <dt>{{ _t('Host alias') }}</dt>
      <dd>{{ data.host_alias }}</dd>

      <dt>{{ _t('Host state') }}</dt>
      <dd>
        <HostStateDisplay :state="data.host_state" />
      </dd>
    </OverviewDetailList>

    <div class="monitoring-service-overview-tab__links">
      <CmkLink :href="data.legacy_host_status_link" target="_top">
        {{ _t('Show host details') }}
      </CmkLink>
      <CmkLink :href="data.legacy_service_status_link" target="_top">
        {{ _t('Show service details') }}
      </CmkLink>
    </div>
  </div>
</template>

<style scoped>
.monitoring-service-overview-tab {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-double);
}

.monitoring-service-overview-tab__links {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
  align-items: flex-start;
}
</style>
