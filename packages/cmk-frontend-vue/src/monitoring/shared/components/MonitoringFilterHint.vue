<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts" generic="T">
import type { UnappliedFilter } from 'cmk-shared-typing/typescript/monitoring/unapplied_filter'
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

import type { MonitoringService } from '@/monitoring/shared/services/MonitoringService'

const { _t } = usei18n()

const props = defineProps<{
  /** The filters of the legacy view the page was opened from that it does not apply. */
  unappliedFilters: UnappliedFilter[]
  /** The service of the table whose filters the hint is about. */
  service: MonitoringService<T>
}>()

// The unapplied filters are those the page was opened with. Once the user set the filters, e.g.
// added the condition a filter named here stood for or reset them all, naming them would be out
// of date. A search takes over none of them, so it leaves them named.
const unappliedTitles = computed(() =>
  props.service.filtersUpdatedSinceLoad.value
    ? ''
    : props.unappliedFilters.map((filter) => filter.title).join(', ')
)

const filtersInHiddenColumns = computed(() => props.service.hiddenFilteredColumnIds.value.size > 0)

const text = computed<TranslatedString | null>(() => {
  const filters = unappliedTitles.value
  if (filters !== '' && filtersInHiddenColumns.value) {
    return _t('Some filters not supported yet: %{filters}; others active in hidden columns', {
      filters
    })
  }
  if (filters !== '') {
    return _t('Some filters not supported yet: %{filters}', { filters })
  }
  if (filtersInHiddenColumns.value) {
    return _t('Filters active in hidden columns')
  }
  return null
})
</script>

<template>
  <CmkAlert v-if="text !== null" variant="info" size="small" :text="text" />
</template>
