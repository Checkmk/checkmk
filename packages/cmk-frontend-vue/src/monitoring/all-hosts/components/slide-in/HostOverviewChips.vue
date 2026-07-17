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
import CmkTag from '@/components/CmkTag.vue'

const DEFAULT_LIMIT = 5

const props = withDefaults(defineProps<{ items: string[]; limit?: number }>(), {
  limit: DEFAULT_LIMIT
})

const { _t } = usei18n()

const expanded = ref(false)

const hasOverflow = computed(() => props.items.length > props.limit)
const visibleItems = computed<TranslatedString[]>(
  () => (expanded.value ? props.items : props.items.slice(0, props.limit)) as TranslatedString[]
)
</script>

<template>
  <div class="monitoring-host-overview-chips">
    <CmkTag v-for="item in visibleItems" :key="item" size="small" variant="fill" :content="item" />
    <CmkButton v-if="hasOverflow" size="small" variant="optional" @click="expanded = !expanded">
      {{ expanded ? _t('show less') : `+${items.length - limit}` }}
    </CmkButton>
  </div>
</template>

<style scoped>
.monitoring-host-overview-chips {
  display: flex;
  flex-flow: row wrap;
  gap: var(--dimension-3);
  align-items: center;
}
</style>
