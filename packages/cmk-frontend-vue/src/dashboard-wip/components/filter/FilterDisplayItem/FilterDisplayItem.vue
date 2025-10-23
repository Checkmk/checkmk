<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import { useFilterDefinitions } from '@/dashboard-wip/components/filter/utils.ts'

import type { ConfiguredValues } from '../types.ts'
import FilterDisplayComponentRenderer from './FilterDisplayComponentRenderer.vue'

interface Props {
  filterId: string
  configuredValues: ConfiguredValues
}

const props = defineProps<Props>()

const filterDefinitions = useFilterDefinitions()
const filterDefinition = filterDefinitions[props.filterId]
if (!filterDefinition) {
  throw new Error(`Filter definition for ${props.filterId} not found`)
}

const components = computed(() => {
  return filterDefinition.extensions.components || []
})
</script>

<template>
  <div class="filter-container">
    <div class="filter-title">
      {{ filterDefinition.title }}
    </div>
    <div class="filter-components">
      <FilterDisplayComponentRenderer
        v-for="(component, index) in components"
        :key="index"
        :component="component"
        :configured-filter-values="configuredValues"
      />
    </div>
  </div>
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-title {
  font-weight: var(--font-weight-bold);
  font-size: var(--font-size-normal);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-components {
  width: 100%;
  display: flex;
  margin-top: var(--dimension-2);
  flex-direction: column;
  gap: var(--dimension-6);
  justify-content: space-between;
}
</style>
