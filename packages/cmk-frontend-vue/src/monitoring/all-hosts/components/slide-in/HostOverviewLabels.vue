<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkButton from '@/components/CmkButton/CmkButton.vue'
import CmkTag, { type Colors } from '@/components/CmkTag.vue'

import type { HostOverview } from '@/monitoring/shared/api/types'

const DEFAULT_LIMIT = 5

const props = withDefaults(defineProps<{ labels: HostOverview['labels']; limit?: number }>(), {
  limit: DEFAULT_LIMIT
})

const { _t } = usei18n()

const SOURCE_COLORS: Record<string, Colors> = {
  discovered: 'discovered',
  explicit: 'explicit',
  ruleset: 'ruleset'
}

const expanded = ref(false)

const items = computed(() =>
  Object.entries(props.labels).map(([key, label]) => ({
    text: `${key}: ${label.value}` as TranslatedString,
    color: SOURCE_COLORS[label.source] ?? 'default'
  }))
)

const hasOverflow = computed(() => items.value.length > props.limit)
const visibleItems = computed(() =>
  expanded.value ? items.value : items.value.slice(0, props.limit)
)
</script>

<template>
  <div class="monitoring-host-overview-labels">
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
.monitoring-host-overview-labels {
  display: flex;
  flex-flow: row wrap;
  gap: var(--dimension-3);
  align-items: center;
}
</style>
