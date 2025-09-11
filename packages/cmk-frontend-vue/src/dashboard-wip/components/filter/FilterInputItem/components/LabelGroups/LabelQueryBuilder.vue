<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkDropdown from '@/components/CmkDropdown.vue'
import CmkLabel from '@/components/CmkLabel.vue'
import CmkList from '@/components/CmkList'

import type { LabelQueryBuilderConfig } from '../../../types.ts'
import LabelGroup from './LabelGroup.vue'
import type { LabelGroupItem, QueryItem } from './types.ts'

interface Props {
  component: LabelQueryBuilderConfig
}

defineProps<Props>()

const { _t } = usei18n()

const model = defineModel<QueryItem[]>({
  default: () => [{ groups: [{ operator: 'and', label: null }], operator: 'and' }]
})

const operatorChoices = [
  { name: 'and', title: _t('and') },
  { name: 'or', title: _t('or') },
  { name: 'not', title: _t('not') }
]

const itemsProps = computed(() => ({
  operator: model.value.map((queryItem) => queryItem.operator),
  labelGroups: model.value.map((queryItem) => queryItem.groups)
}))

function tryDelete(index: number): boolean {
  if (model.value.length <= 1) {
    return false
  }

  const newValue = [...model.value]
  newValue.splice(index, 1)
  model.value = newValue
  return true
}

function tryAdd(_index: number): boolean {
  const newGroup: QueryItem = {
    operator: operatorChoices[0]!.name,
    groups: [{ operator: 'and', label: null }]
  }

  model.value = [...model.value, newGroup]
  return true
}

function updateGroupOperator(index: number, operator: string | null) {
  if (index === 0) {
    // First group doesn't have operator
    return
  }

  const newValue = [...model.value]
  newValue[index] = { ...newValue[index]!, operator: operator! }
  model.value = newValue
}

function updateLabelGroup(index: number, groups: LabelGroupItem[]) {
  const newValue = [...model.value]
  newValue[index] = { operator: newValue[index]!.operator, groups }
  model.value = newValue
}

// Initialize with default value if empty
if (model.value.length === 0) {
  model.value = [{ operator: 'and', groups: [{ operator: 'and', label: null }] }]
}
</script>

<template>
  <div class="query-builder">
    <CmkList
      :items-props="itemsProps"
      :try-delete="tryDelete"
      :add="{ show: true, tryAdd, label: 'Add to query' }"
      orientation="vertical"
    >
      <template #item-props="{ index, operator, labelGroups }">
        <div class="query-group">
          <div class="query-group__operator">
            <CmkLabel v-if="index === 0">{{ _t('Label') }}</CmkLabel>
            <CmkDropdown
              v-else
              :options="{ type: 'fixed', suggestions: operatorChoices }"
              :label="_t('Group Operator')"
              :selected-option="operator"
              @update:selected-option="(value: string | null) => updateGroupOperator(index, value)"
            />
          </div>
          <div class="query-group__content">
            <LabelGroup
              :model-value="labelGroups"
              @update:model-value="(value: LabelGroupItem[]) => updateLabelGroup(index, value)"
            />
          </div>
        </div>
      </template>
    </CmkList>
  </div>
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.query-builder {
  display: flex;
  flex-direction: column;
  gap: var(--spacing);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.query-group {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing);
  width: 100%;
  padding-top: var(--dimension-2);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.query-group__operator {
  width: 80px;
  flex-shrink: 0;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.query-group__content {
  flex: 1;
  min-width: 0;
}
</style>
