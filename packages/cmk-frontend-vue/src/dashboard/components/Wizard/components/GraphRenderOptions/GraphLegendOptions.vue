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
import { computed } from 'vue'

import RadioButton from '@/dashboard/components/Wizard/components/RadioButton.vue'
import type { GraphLegendStyle } from '@/dashboard/components/Wizard/types'

const { _t } = usei18n()

const showLegend = defineModel<boolean>('showLegend', { required: true })
const legendStyle = defineModel<GraphLegendStyle>('legendStyle', { required: true })

const name = useId()
const style = computed({
  get: (): string => legendStyle.value,
  set: (value: string) => {
    legendStyle.value = value === 'extended' ? 'extended' : 'compact'
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
