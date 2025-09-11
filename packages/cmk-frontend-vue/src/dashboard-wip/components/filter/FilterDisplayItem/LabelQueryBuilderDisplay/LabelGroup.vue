<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkLabel from '@/components/CmkLabel.vue'

import type { LabelGroupItem } from '../../FilterInputItem/components/LabelGroups/types.ts'

interface Props {
  modelValue: LabelGroupItem[]
}

const { _t } = usei18n()

const props = defineProps<Props>()

const operatorDisplayMap: Record<string, string> = {
  and: _t('is'),
  not: _t('is not'),
  or: _t('or')
}

const displayItems = computed(() => {
  return props.modelValue.filter((item) => item.label !== null && item.label !== '')
})
</script>

<template>
  <div class="readonly-label-group">
    <div v-if="displayItems.length === 0">
      <CmkLabel> {{ _t('No labels') }} </CmkLabel>
    </div>
    <div v-else class="label-items">
      <div v-for="(item, index) in displayItems" :key="index" class="label-item">
        <span class="label-item__operator">
          <CmkLabel>
            {{ index === 0 ? operatorDisplayMap[item.operator] || item.operator : item.operator }}
          </CmkLabel>
        </span>
        <CmkLabel>
          {{ item.label }}
        </CmkLabel>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.readonly-label-group {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.label-items {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-1);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.label-item {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  padding: var(--dimension-1) 0;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.label-item__operator {
  min-width: 40px;
}
</style>
