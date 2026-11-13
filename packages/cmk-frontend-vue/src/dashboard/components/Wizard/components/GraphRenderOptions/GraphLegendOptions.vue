<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIndent from 'cmk-ui-library/components/CmkIndent.vue'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import useId from 'cmk-ui-library/lib/useId'
import { computed, ref } from 'vue'

import RadioButton from '@/dashboard/components/Wizard/components/RadioButton.vue'
import type { GraphLegend, GraphLegendStyle } from '@/dashboard/components/Wizard/types'

const { _t } = usei18n()

const legend = defineModel<GraphLegend>('legend', { required: true })

const name = useId()
const lastStyle = ref<GraphLegendStyle>(legend.value === 'none' ? 'compact' : legend.value)
const showLegend = computed({
  get: (): boolean => legend.value !== 'none',
  set: (show: boolean) => {
    legend.value = show ? lastStyle.value : 'none'
  }
})
const style = computed({
  get: (): string => (legend.value === 'none' ? lastStyle.value : legend.value),
  set: (value: string) => {
    lastStyle.value = value === 'extended' ? 'extended' : 'compact'
    legend.value = lastStyle.value
  }
})
</script>

<template>
  <CmkCheckbox v-model:model-value="showLegend" :label="_t('Show graph legend')" />
  <CmkIndent v-if="showLegend">
    <div class="db-graph-legend-options__option">
      <RadioButton v-model="style" :name="name" value="compact" :label="_t('Compact')" />
    </div>
    <div class="db-graph-legend-options__option">
      <RadioButton v-model="style" :name="name" value="extended" :label="_t('Extended')" />
    </div>
  </CmkIndent>
</template>

<style scoped>
.db-graph-legend-options__option {
  padding-top: var(--spacing-half);
}
</style>
