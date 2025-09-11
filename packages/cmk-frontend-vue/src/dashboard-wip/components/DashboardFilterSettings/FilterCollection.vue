<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkLabel from '@/components/CmkLabel.vue'

import type { ConfiguredValues } from '@/dashboard-wip/components/filter/types.ts'

interface Props {
  title: string
  filters: string[]
  getFilterValues: (filterId: string) => ConfiguredValues | null
  additionalItemLabel?: string | null
}

withDefaults(defineProps<Props>(), {
  additionalItemLabel: null
})
</script>

<template>
  <div class="dashboard-filter__collection">
    <div class="dashboard-filter__collection-title">
      <CmkLabel variant="title">{{ title }}</CmkLabel>
    </div>
    <div v-for="(filterId, index) in filters" :key="index" class="filter-item__container">
      <slot
        :filter-id="filterId"
        :configured-filter-values="getFilterValues(filterId)"
        :index="index"
      />
    </div>
    <div v-if="additionalItemLabel" class="dashboard-filter__item-placeholder">
      {{ additionalItemLabel }}
    </div>
  </div>
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.dashboard-filter__collection {
  margin-top: var(--dimension-7);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.dashboard-filter__collection-title {
  margin-bottom: var(--dimension-4);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.filter-item__container {
  background-color: var(--ux-theme-3);
  margin-bottom: var(--dimension-4);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.dashboard-filter__item-placeholder {
  padding: var(--dimension-5) var(--dimension-7);
  border: 1px dashed var(--ux-theme-7);
  color: var(--color-white-70);
}
</style>
