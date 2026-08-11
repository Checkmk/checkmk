<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton/CmkButton.vue'
import CmkTag from 'cmk-ui-library/components/CmkTag.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, ref } from 'vue'

import type { LabelValue } from '@/monitoring/shared/api/types'
import { toLabelItems } from '@/monitoring/shared/labels'

const DEFAULT_LIMIT = 5

const props = withDefaults(defineProps<{ labels: Record<string, LabelValue>; limit?: number }>(), {
  limit: DEFAULT_LIMIT
})

const { _t } = usei18n()

const expanded = ref(false)

const items = computed(() => toLabelItems(props.labels))

const hasOverflow = computed(() => items.value.length > props.limit)
const visibleItems = computed(() =>
  expanded.value ? items.value : items.value.slice(0, props.limit)
)
</script>

<template>
  <div class="monitoring-overview-labels">
    <CmkTag
      v-for="item in visibleItems"
      :key="item.text"
      size="small"
      variant="fill"
      :color="item.color"
      :content="item.text"
    />
    <CmkButton v-if="hasOverflow" size="small" variant="optional" @click="expanded = !expanded">
      {{ expanded ? _t('show less') : `+${items.length - limit}` }}
    </CmkButton>
  </div>
</template>

<style scoped>
.monitoring-overview-labels {
  display: flex;
  flex-flow: row wrap;
  gap: var(--dimension-3);
  align-items: center;
}
</style>
