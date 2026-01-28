<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'

import usei18n from '@/lib/i18n'

import CmkHeading from '@/components/typography/CmkHeading.vue'

import FilterDisplayItem from '@/dashboard/components/filter/FilterDisplayItem/FilterDisplayItem.vue'
import type { ConfiguredFilters } from '@/dashboard/components/filter/types'
import { useFilterDefinitions } from '@/dashboard/components/filter/utils'

import { type MetricSelection } from '../../wizards/metrics/composables/useSelectGraphTypes'
import ContentSpacer from '../ContentSpacer.vue'
import { splitFiltersByCategory, squashFilters } from './utils'

const { _t } = usei18n()

interface FiltersRecapProps {
  contextConfiguredFilters: ConfiguredFilters
  widgetFilters?: ConfiguredFilters

  metricType?: MetricSelection | null
  metric?: string | null

  customValue?: string | null
  customValueTitle?: string | null
}

const props = withDefaults(defineProps<FiltersRecapProps>(), {
  widgetFilters: () => {
    return {} as ConfiguredFilters
  },
  metricType: null,
  metric: null,
  customValue: null,
  customValueTitle: null
})

const filterDefinitions = useFilterDefinitions()

const allFiltersByCategory: Record<string, ConfiguredFilters> = splitFiltersByCategory(
  squashFilters(props.contextConfiguredFilters, props.widgetFilters),
  filterDefinitions!
)

const MAX_PREVIEW_ITEMS = 5
const showAllHosts = ref<boolean>(false)
const showAllServices = ref<boolean>(false)

const _getFilterSubset = (collection: ConfiguredFilters): ConfiguredFilters => {
  const selectedFilters = Object.keys(collection).slice(0, MAX_PREVIEW_ITEMS)
  const filtersSubset: ConfiguredFilters = {}
  for (const flt of selectedFilters) {
    filtersSubset[flt] = collection[flt] || {}
  }
  return filtersSubset
}

const hostFilters = computed((): ConfiguredFilters => {
  const collection = allFiltersByCategory['host']!
  if (showAllHosts.value) {
    return collection
  }

  return _getFilterSubset(collection)
})

const serviceFilters = computed((): ConfiguredFilters => {
  const collection = allFiltersByCategory['service']!
  if (showAllServices.value) {
    return collection
  }

  return _getFilterSubset(collection)
})

const hostFiltersCount = computed((): number => {
  return Object.keys(allFiltersByCategory['host']!).length
})

const serviceFiltersCount = computed((): number => {
  return Object.keys(allFiltersByCategory['service']!).length
})
</script>

<template>
  <div v-if="hostFiltersCount > 0">
    <CmkHeading type="h2">{{ _t('Hosts') }}</CmkHeading>
    <div class="filters-recap__category-container">
      <FilterDisplayItem
        v-for="(configuredValues, flt) of hostFilters"
        :key="flt"
        :filter-id="flt"
        :configured-values="configuredValues"
      />
    </div>
    <div v-if="!showAllHosts && hostFiltersCount > MAX_PREVIEW_ITEMS">
      <a href="#" @click.prevent="showAllHosts = true"
        >{{ _t('See all') }} {{ hostFiltersCount }}</a
      >
    </div>

    <ContentSpacer variant="line" />
  </div>

  <div v-if="serviceFiltersCount > 0">
    <CmkHeading type="h2">{{ _t('Services') }}</CmkHeading>
    <div class="filters-recap__category-container">
      <FilterDisplayItem
        v-for="(configuredValues, flt) of serviceFilters"
        :key="flt"
        :filter-id="flt"
        :configured-values="configuredValues"
      />
    </div>
    <div v-if="!showAllServices && serviceFiltersCount > MAX_PREVIEW_ITEMS">
      <a href="#" @click.prevent="showAllServices = true"
        >{{ _t('See all') }} {{ serviceFiltersCount }}</a
      >
    </div>

    <ContentSpacer variant="line" />
  </div>

  <div v-if="!!metricType">
    <CmkHeading type="h3">{{ _t('Metric') }}</CmkHeading>
    <div class="filter-recap__content">
      <ul class="db-filters-recap__list">
        <li>{{ props.metric }}</li>
      </ul>
    </div>
  </div>

  <div v-if="!!customValue">
    <CmkHeading type="h3">{{ customValueTitle }}</CmkHeading>
    <div class="filter-recap__content">
      <ul class="db-filters-recap__list">
        <li>{{ props.customValue }}</li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.db-filters-recap__list {
  list-style: none;
  margin: 0;
  padding: 0;
}
</style>
