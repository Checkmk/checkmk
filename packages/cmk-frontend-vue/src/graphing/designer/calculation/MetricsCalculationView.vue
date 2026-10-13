<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import CmkScrollContainer from 'cmk-ui-library/components/CmkScrollContainer.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { onMounted, ref } from 'vue'

import type { FormulaDraft, GraphItem, ItemId } from '../types'
import RrdTab from './components/RrdTab.vue'
import type { RefVisibility } from './composables/useCalculationEditor'

const { _t } = usei18n()

const { editing, items, nextId, nextColor } = defineProps<{
  /** Calculation to load into the form; null starts a fresh form. */
  editing: ItemId | null
  items: readonly GraphItem[]
  /** Id the next added item will get. */
  nextId: ItemId
  /** Default color for the next added item. */
  nextColor: string
}>()

const emit = defineEmits<{
  add: [draft: FormulaDraft, refVisibility: RefVisibility]
  update: [id: ItemId, draft: FormulaDraft, refVisibility: RefVisibility]
  delete: [id: ItemId]
  close: []
}>()

const rrdTabRef = ref<InstanceType<typeof RrdTab> | null>(null)

onMounted(() => rrdTabRef.value?.focus())
</script>

<template>
  <div class="graphing-metrics-calculation-view">
    <CmkButton
      variant="optional"
      class="graphing-metrics-calculation-view__back"
      @click="emit('close')"
    >
      <CmkIcon name="back" size="small" />
      {{ _t('Back to metrics selection') }}
    </CmkButton>
    <CmkScrollContainer
      height="auto"
      max-height="none"
      class="graphing-metrics-calculation-view__container"
    >
      <RrdTab
        ref="rrdTabRef"
        :editing="editing"
        :items="items"
        :next-id="nextId"
        :next-color="nextColor"
        @add="(draft, refVisibility) => emit('add', draft, refVisibility)"
        @update="(id, draft, refVisibility) => emit('update', id, draft, refVisibility)"
        @delete="emit('delete', $event)"
      />
    </CmkScrollContainer>
  </div>
</template>

<style scoped>
.graphing-metrics-calculation-view {
  display: flex;
  flex-direction: column;
  flex: 0 1 auto;
  min-height: 0;
  gap: var(--dimension-7);
}

.graphing-metrics-calculation-view__back {
  flex-shrink: 0;
  align-self: flex-start;
  gap: var(--dimension-3);
}

.graphing-metrics-calculation-view__container {
  flex: 0 1 auto;
  min-height: 0;
  padding: var(--dimension-5) var(--dimension-7) var(--dimension-7);
  background: var(--ux-theme-2);
  border: 1px solid var(--border-color-subtle);
}
</style>
