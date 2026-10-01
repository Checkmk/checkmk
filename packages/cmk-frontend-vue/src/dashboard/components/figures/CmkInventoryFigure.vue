<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import ContextualLinkTrigger from '@/dashboard/components/ContextualLinkTrigger.vue'
import type { InventoryAttribute, VisualContext } from '@/dashboard/types/widget'

import { valueFontSize } from './lib/valueFontSize'

const props = defineProps<{
  value: InventoryAttribute
  width: number
  height: number
  filters: VisualContext
  interactive: boolean
}>()

const { _t } = usei18n()

const fontSizePx = computed(() => `${valueFontSize(props.width, props.height)}px`)
</script>

<template>
  <svg
    role="figure"
    class="db-cmk-inventory-figure"
    :width="width"
    :height="height"
    :viewBox="`0 0 ${width} ${height}`"
  >
    <ContextualLinkTrigger
      :links="value.links"
      :link-properties="value.link_properties"
      :filters="filters"
      :interactive="interactive"
    >
      <foreignObject :width="width" :height="height">
        <div class="db-cmk-inventory-figure__box">
          <div class="db-cmk-inventory-figure__value">{{ value.value ?? _t('n/a') }}</div>
        </div>
      </foreignObject>
    </ContextualLinkTrigger>
  </svg>
</template>

<style scoped>
.db-cmk-inventory-figure {
  display: block;
}

.db-cmk-inventory-figure__box {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
}

.db-cmk-inventory-figure__value {
  width: 100%;
  color: var(--font-color);
  font-size: v-bind(fontSizePx);
  font-weight: var(--font-weight-bold);
  text-align: center;
  overflow-wrap: break-word;
}
</style>
