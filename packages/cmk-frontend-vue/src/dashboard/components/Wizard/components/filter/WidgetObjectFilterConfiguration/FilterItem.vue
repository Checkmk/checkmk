<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'

import FilterDisplayItem from '@/dashboard/components/filter/FilterDisplayItem/FilterDisplayItem.vue'
import type { ConfiguredValues } from '@/dashboard/components/filter/types'
import { FilterOrigin } from '@/dashboard/types/filter'

import ContentSpacer from '../../ContentSpacer.vue'

const { _t } = usei18n()

const LABEL_INHERITED = _t('Inherited')
const LABEL_OVERRIDDEN = _t('Overridden')

interface FilterItemProp {
  overridden?: boolean
  filterId: string
  origin: FilterOrigin
  configuredValues: ConfiguredValues
}

const props = withDefaults(defineProps<FilterItemProp>(), {
  overridden: false
})

const originLabel = computed<TranslatedString>(() => {
  switch (props.origin) {
    case FilterOrigin.DASHBOARD:
      return _t('Default filter')
    case FilterOrigin.QUICK_FILTER:
      return _t('Runtime filter')
    case FilterOrigin.LINKED_VIEW:
      return _t('View filter')
    default:
      throw new Error(`Unknown filter origin: ${props.origin}`)
  }
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
      {{ overridden ? LABEL_OVERRIDDEN : LABEL_INHERITED }}
    </div>

    <div class="db-filter-item__component">
      {{ originLabel }}
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
  padding-right: var(--dimension-5);
}

.db-filter-item__disabled-icon {
  --icon-primary-color: var(--font-color-dimmed);
}
</style>
