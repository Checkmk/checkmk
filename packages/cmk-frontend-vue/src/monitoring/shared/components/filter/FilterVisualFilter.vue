<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<!--
Funnel content for a registered visuals filter: renders whatever that filter
declares, through the same CmkFilterInputItem the dashboard's filter settings
use, so a filter needs no per-column UI of its own.

Its model is the filter's ConfiguredValues rather than a column condition. A set
of values that are all blank means "not set", and becomes undefined - otherwise
opening a funnel and typing nothing would leave the column looking filtered.
-->
<script setup lang="ts">
import { CmkFilterInputItem, type ConfiguredValues } from 'cmk-ui-library/components/filter'

import type { VisualFilterColumnFilter } from './types'

defineProps<{ definition: VisualFilterColumnFilter }>()

const model = defineModel<ConfiguredValues | undefined>({ default: undefined })

function onUpdateFilterValues(_filterId: string, values: ConfiguredValues): void {
  model.value = Object.values(values).some((value) => value.trim() !== '') ? values : undefined
}
</script>

<template>
  <div class="monitoring-filter-visual-filter">
    <CmkFilterInputItem
      :filter-id="definition.filterId"
      :configured-filter-values="model ?? null"
      @update-filter-values="onUpdateFilterValues"
    />
  </div>
</template>

<style scoped>
.monitoring-filter-visual-filter {
  min-width: 260px;
}
</style>
