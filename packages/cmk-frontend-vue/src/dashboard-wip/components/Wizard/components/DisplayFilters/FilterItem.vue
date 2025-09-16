<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkIcon from '@/components/CmkIcon.vue'

import FilterDisplayItem from '@/dashboard-wip/components/filter/FilterDisplayItem/FilterDisplayItem.vue'
import type { ConfiguredValues } from '@/dashboard-wip/components/filter/types'

import type { FilterOrigin } from '../HostServiceSelector/types'

const { _t } = usei18n()

const LABEL_INHERITED = _t('Inherited')
const LABEL_OVERRIDEN = _t('Overriden')

const LABEL_ORIGIN_DASHBOARD = _t('Dashboard filter')
const LABEL_ORIGIN_QUICK_FILTER = _t('Quick filter')

interface FilterItemProp {
  overridden?: boolean
  filterId: string
  origin: FilterOrigin
  configuredValues: ConfiguredValues
}

withDefaults(defineProps<FilterItemProp>(), {
  overridden: false
})
</script>

<template>
  <div class="db-filter-item__item" :class="overridden ? 'db-filter-item--disabled' : ''">
    <div class="db-filter-item__component">
      <CmkIcon :name="overridden ? 'icon_disabled' : 'icon_enabled'" size="xsmall" />
    </div>

    <div class="db-filter-item__component">
      <FilterDisplayItem :filter-id="filterId" :configured-values="configuredValues" />
    </div>

    <div class="db-filter-item__component">
      {{ overridden ? LABEL_OVERRIDEN : LABEL_INHERITED }}
    </div>

    <div class="db-filter-item__component">
      {{ origin === 'DASHBOARD' ? LABEL_ORIGIN_DASHBOARD : LABEL_ORIGIN_QUICK_FILTER }}
    </div>
  </div>
</template>

<style scoped>
.db-filter-item--disabled {
  color: var(--ux-theme-9);
}

.db-filter-item__item {
  display: flex;
  flex-flow: row nowrap;
  place-content: normal;
  align-content: normal;
  gap: var(--spacing);
}

.db-filter-item__component:nth-child(1) {
  display: block;
  flex-grow: 0;
  flex-shrink: 1;
  align-self: auto;
  order: 0;
}

.db-filter-item__component:nth-child(2) {
  display: block;
  flex-grow: 1;
  flex-shrink: 1;
  align-self: auto;
  order: 0;
}

.db-filter-item__component:nth-child(3) {
  display: block;
  flex-grow: 0;
  flex-shrink: 1;
  align-self: auto;
  order: 0;
}

.db-filter-item__component:nth-child(4) {
  display: block;
  flex-grow: 0;
  flex-shrink: 1;
  align-self: auto;
  order: 0;
  padding-right: var(--spacing);
}
</style>
