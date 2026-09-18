<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

import { type Domain, type GraphItem, type ItemId, domainOf, isFormula } from '../../types'
import ItemListSection, { type SectionAlert } from './ItemListSection.vue'

const { _t } = usei18n()

const {
  items,
  domain,
  actionLabel,
  itemBlockReason,
  alert = null
} = defineProps<{
  items: readonly GraphItem[]
  domain: Domain
  actionLabel: (id: ItemId) => TranslatedString
  itemBlockReason?: ((item: GraphItem) => TranslatedString | null) | undefined
  alert?: SectionAlert | null | undefined
}>()

const emit = defineEmits<{
  insertId: [id: ItemId]
  edit: [id: ItemId]
  delete: [id: ItemId]
  dismissAlert: []
}>()

const inDomain = computed(() => items.filter((item) => domainOf(item.type) === domain))
const calculations = computed(() => inDomain.value.filter(isFormula))
const sourceMetrics = computed(() => inDomain.value.filter((item) => !isFormula(item)))
</script>

<template>
  <div class="graphing-item-list-panel">
    <ItemListSection
      :heading="_t('Calculations')"
      :empty-text="_t('No calculations yet.')"
      :items="calculations"
      :action-label="actionLabel"
      :item-block-reason="itemBlockReason"
      :alert="alert"
      show-actions
      @insert-id="emit('insertId', $event)"
      @edit="emit('edit', $event)"
      @delete="emit('delete', $event)"
      @dismiss-alert="emit('dismissAlert')"
    />
    <ItemListSection
      :heading="_t('Source metrics')"
      :empty-text="_t('No metrics available.')"
      :items="sourceMetrics"
      :action-label="actionLabel"
      :item-block-reason="itemBlockReason"
      @insert-id="emit('insertId', $event)"
    />
  </div>
</template>

<style scoped>
.graphing-item-list-panel {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-7);
}
</style>
