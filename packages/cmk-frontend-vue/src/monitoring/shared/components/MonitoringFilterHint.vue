<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="T">
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { MonitoringService } from '@/monitoring/shared/services/MonitoringService'

const { _t } = usei18n()

const props = defineProps<{
  /** The service of the table whose filters the hint is about. */
  service: MonitoringService<T>
}>()

const filtersInHiddenColumns = computed(() => props.service.hiddenFilteredColumnIds.value.size > 0)
</script>

<template>
  <CmkAlert
    v-if="filtersInHiddenColumns"
    variant="info"
    size="small"
    :text="_t('Filters active in hidden columns')"
  />
</template>
