<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import ActionButton from '@/dashboard-wip/components/Wizard/components/ActionButton.vue'
import type { FilterConfigState } from '@/dashboard-wip/components/Wizard/components/filter/utils.ts'
import FilterInputItem from '@/dashboard-wip/components/filter/FilterInputItem/FilterInputItem.vue'
import type { ConfiguredValues } from '@/dashboard-wip/components/filter/types.ts'
import type { ObjectType } from '@/dashboard-wip/types/shared.ts'

import AddFilterMessage from './AddFilterMessage.vue'

interface Props {
  objectType: ObjectType
  objectConfiguredFilters: FilterConfigState
  inFocus: boolean
}

defineProps<Props>()

const emit = defineEmits<{
  (e: 'set-focus', target: ObjectType): void
  (e: 'update-filter-values', filterId: string, values: ConfiguredValues): void
}>()

const { _t } = usei18n()
</script>

<template>
  <FilterInputItem
    v-for="(configuredValues, name) in objectConfiguredFilters"
    :key="name as string"
    :filter-id="name as string"
    :configured-filter-values="configuredValues"
    @update-filter-values="
      (id: string, values: ConfiguredValues) => emit('update-filter-values', id, values)
    "
  />
  <ActionButton
    v-if="!inFocus"
    :label="_t('Add filter')"
    :icon="{ name: 'icon-plus', side: 'left' }"
    variant="secondary"
    :action="
      () => {
        emit('set-focus', objectType)
      }
    "
  />
  <AddFilterMessage v-else />
</template>
