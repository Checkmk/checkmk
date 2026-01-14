<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'

import FilterDisplayItem from '@/dashboard/components/filter/FilterDisplayItem/FilterDisplayItem.vue'
import type { ConfiguredValues } from '@/dashboard/components/filter/types'
import type { FilterOrigin } from '@/dashboard/types/filter'

import ContentSpacer from '../../ContentSpacer.vue'

const { _t } = usei18n()

const LABEL_INHERITED = _t('Inherited')
const LABEL_OVERRIDEN = _t('Overriden')

const LABEL_ORIGIN_DASHBOARD = _t('Default filter')
const LABEL_ORIGIN_QUICK_FILTER = _t('Runtime filter')

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
      <CmkMultitoneIcon
        :name="overridden ? 'broken-chain' : 'chain'"
        primary-color="font"
        size="small"
        :class="{ 'db-filter-item__disabled-icon': overridden }"
      />
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
  <ContentSpacer :dimension="5" />
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
  gap: var(--dimension-4);
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

.db-filter-item__disabled-icon {
  --icon-primary-color: var(--font-color-dimmed);
}
</style>
