<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkInlineValidation from 'cmk-ui-library/components/user-input/CmkInlineValidation.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

import ItemIdChip from '../../calculation/components/ItemIdChip.vue'
import { collectDirectRefs } from '../../calculation/formula'
import type { GraphItemsStore } from '../../composables/useGraphItems'
import { useItemDescription } from '../../composables/useItemDescription'
import type { DesignerItem } from '../../drafts'
import { type FormulaItem, isSingleLine } from '../../types'
import { isValid } from '../../validation'

const { item, store, astErrors } = defineProps<{
  item: FormulaItem
  store: GraphItemsStore
  astErrors: TranslatedString[]
}>()

const { _t } = usei18n()
const { describeItem } = useItemDescription()

/** The sources the formula references directly, resolved to their table rows. */
const referencedItems = computed<DesignerItem[]>(() => {
  const byId = new Map(store.items.value.map((candidate) => [candidate.id, candidate]))
  return collectDirectRefs(item.ast)
    .map((id) => byId.get(id))
    .filter((candidate): candidate is DesignerItem => candidate !== undefined)
})

function chipColor(referenced: DesignerItem): string | undefined {
  return isSingleLine(referenced) ? referenced.color : undefined
}
</script>

<template>
  <div class="graphing-formula-form">
    <span>{{ describeItem(item) }}</span>

    <CmkInlineValidation v-if="astErrors.length > 0" :validation="astErrors" />

    <div v-if="referencedItems.length > 0" class="graphing-formula-form__listing">
      <template v-for="referenced in referencedItems" :key="referenced.id">
        <ItemIdChip :id="referenced.id" :color="chipColor(referenced)" />
        <span class="graphing-formula-form__desc">{{
          isValid(referenced) ? describeItem(referenced) : _t('incomplete source')
        }}</span>
      </template>
    </div>
  </div>
</template>

<style scoped>
.graphing-formula-form {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

.graphing-formula-form__listing {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: var(--dimension-4) var(--dimension-5);
  align-items: center;
}

.graphing-formula-form__desc {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
