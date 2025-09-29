<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkIcon from '@/components/CmkIcon.vue'
import CmkLabel from '@/components/CmkLabel.vue'

import type { FilterDefinition } from '@/dashboard-wip/components/filter/types.ts'

interface Props {
  title: string
  filters: string[]
  filterDefinitions: Record<string, FilterDefinition>
}

const { _t } = usei18n()
const props = defineProps<Props>()

const emit = defineEmits<{
  removeFilter: [filterId: string]
}>()

const handleRemoveFilter = (filterId: string) => {
  emit('removeFilter', filterId)
}
</script>

<template>
  <div class="quick-filter__collection">
    <div class="quick-filter__collection-title">
      <CmkLabel variant="title">{{ title }}</CmkLabel>
    </div>
    <div v-for="(filterId, index) in filters" :key="index" class="quick-filter__item">
      <span class="quick-filter__item-title">
        {{ props.filterDefinitions[filterId]!.title }}
      </span>
      <button
        class="quick-filter__remove-button"
        type="button"
        :aria-label="`Remove ${props.filterDefinitions[filterId]!.title} filter`"
        @click="handleRemoveFilter(filterId)"
      >
        <CmkIcon :aria-label="_t('Remove row')" name="close" size="xxsmall" />
      </button>
    </div>
    <div class="quick-filter__item-placeholder">
      {{ _t('Select from list') }}
    </div>
  </div>
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.quick-filter__collection {
  margin-top: var(--dimension-7);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.quick-filter__collection-title {
  margin-bottom: var(--dimension-4);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.quick-filter__item {
  background-color: var(--ux-theme-3);
  padding: var(--dimension-5) var(--dimension-7);
  margin-bottom: var(--dimension-4);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.quick-filter__item-title {
  flex: 1;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.quick-filter__remove-button {
  background: none;
  border: none;
  color: var(--color-white-70);
  cursor: pointer;
  font-size: var(--dimension-6);
  font-weight: bold;
  margin-left: var(--dimension-4);
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  height: 24px;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.quick-filter__item-placeholder {
  padding: var(--dimension-5) var(--dimension-7);
  border: 1px dashed var(--ux-theme-7);
  color: var(--color-white-70);
}
</style>
