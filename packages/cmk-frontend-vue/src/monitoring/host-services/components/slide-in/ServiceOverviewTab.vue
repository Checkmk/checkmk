<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'

import type { ServiceOverview } from '@/monitoring/shared/api/types'
import OverviewDetailList from '@/monitoring/shared/components/slide-in/OverviewDetailList.vue'

defineProps<{ data: ServiceOverview }>()

const { _t } = usei18n()
</script>

<template>
  <div class="monitoring-service-overview-tab">
    <OverviewDetailList>
      <dt>{{ _t('Service name') }}</dt>
      <dd>{{ data.name }}</dd>
    </OverviewDetailList>
  </div>
</template>

<style scoped>
.monitoring-service-overview-tab {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-double);
}
</style>
