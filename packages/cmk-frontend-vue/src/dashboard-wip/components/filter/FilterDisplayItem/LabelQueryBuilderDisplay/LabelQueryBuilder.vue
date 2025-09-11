<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkLabel from '@/components/CmkLabel.vue'

import type { QueryItem } from '../../FilterInputItem/components/LabelGroups/types.ts'
import type { LabelQueryBuilderConfig } from '../../types.ts'
import LabelGroup from './LabelGroup.vue'

interface Props {
  component: LabelQueryBuilderConfig
  modelValue: QueryItem[]
}

const { _t } = usei18n()
const props = defineProps<Props>()

const operatorDisplayMap: Record<string, string> = {
  and: _t('and'),
  or: _t('or'),
  not: _t('not')
}

const displayGroups = computed(() => {
  return props.modelValue.filter((group) => group.groups.some((item) => item.label !== null))
})
</script>

<template>
  <div class="readonly-query-builder">
    <div v-if="displayGroups.length === 0">
      <CmkLabel>{{ _t('No labels selected') }} </CmkLabel>
    </div>
    <div v-else class="query-groups">
      <div v-for="(queryItem, index) in displayGroups" :key="index" class="query-group">
        <div class="query-group__operator">
          <CmkLabel v-if="index === 0">
            {{ _t('Label') }}
          </CmkLabel>
          <CmkLabel v-else>
            {{ operatorDisplayMap[queryItem.operator] || queryItem.operator }}
          </CmkLabel>
        </div>
        <div class="query-group__content">
          <LabelGroup :model-value="queryItem.groups" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.readonly-query-builder {
  display: flex;
  flex-direction: column;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.query-groups {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-half);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.query-group {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-half);
  width: 100%;
  padding-top: var(--dimension-2);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.query-group__operator {
  width: 40px;
  flex-shrink: 0;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.query-group__content {
  flex: 1;
  min-width: 0;
}
</style>
