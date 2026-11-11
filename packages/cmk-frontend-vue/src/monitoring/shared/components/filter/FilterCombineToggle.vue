<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The AND/OR switch of a filter whose selections can be combined either way.
It only carries the mode; the filter owning it decides what AND and OR mean
for its condition node.
-->
<script setup lang="ts">
import CmkToggleButtonGroup, {
  type ToggleButtonOption
} from 'cmk-ui-library/components/CmkToggleButtonGroup.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import useId from 'cmk-ui-library/lib/useId'
import { computed } from 'vue'

export type CombineMode = 'and' | 'or'

defineProps<{ label: string }>()

const model = defineModel<CombineMode>({ required: true })

const { _t } = usei18n()

const labelId = useId()

const options = computed<ToggleButtonOption[]>(() => [
  { label: _t('AND'), value: 'and' },
  { label: _t('OR'), value: 'or' }
])
</script>

<template>
  <div class="monitoring-filter-combine-toggle" role="group" :aria-labelledby="labelId">
    <span :id="labelId">{{ label }}</span>
    <CmkToggleButtonGroup
      :options="options"
      :model-value="model"
      size="small"
      spacing="none"
      @update:model-value="model = $event as CombineMode"
    />
  </div>
</template>

<style scoped>
.monitoring-filter-combine-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--dimension-4);
}
</style>
