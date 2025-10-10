<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkInlineValidation from '@/components/user-input/CmkInlineValidation.vue'

import AutocompleteHost from '@/dashboard-wip/components/Wizard/components/autocompleters/AutocompleteHost.vue'
import AutocompleteMonitoredMetrics from '@/dashboard-wip/components/Wizard/components/autocompleters/AutocompleteMonitoredMetrics.vue'
import AutocompleteService from '@/dashboard-wip/components/Wizard/components/autocompleters/AutocompleteService.vue'

import { type UseSingleMetric } from './useSingleMetric'

const { _t } = usei18n()

const handler = defineModel<UseSingleMetric>('handler', { required: true })
</script>

<template>
  <div class="db-single-metric__container">
    <div class="row db-single-metric__top-row">
      <div class="db-single-metric__top-cell">
        <AutocompleteHost v-model:host-name="handler.host.value" />
      </div>
      <div class="db-single-metric__top-cell">
        <AutocompleteService v-model:service-description="handler.service.value" />
      </div>
    </div>
    <div class="row db-single-metric__bottom-row">
      <AutocompleteMonitoredMetrics
        v-model:service-metrics="handler.singleMetric.value"
        :host-name="handler.host.value"
        :service-description="handler.service.value"
      />
      <CmkInlineValidation
        v-if="handler.singleMetricValidationError.value"
        :validation="[_t('Must select an option')]"
      />
    </div>
  </div>
</template>

<style scoped>
.db-single-metric__container {
  display: flex;
  flex-direction: column;
}

.db-single-metric__top-row {
  display: flex;
  flex: 1;
}

.db-single-metric__top-cell {
  flex: 1;
  display: flex;
  justify-content: flex-start;
  align-items: flex-start;
  padding-bottom: 10px;
}

.db-single-metric__bottom-row {
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  align-items: flex-start;
}
</style>
