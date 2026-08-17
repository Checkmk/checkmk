<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkCollapsible from 'cmk-ui-library/components/CmkCollapsible'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import CmkInlineValidation from 'cmk-ui-library/components/user-input/CmkInlineValidation.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import useId from 'cmk-ui-library/lib/useId'
import { computed, ref } from 'vue'

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

const validationId = useId()

const open = ref(false)

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
    <button
      type="button"
      class="graphing-formula-form__trigger"
      :aria-expanded="open"
      :aria-invalid="astErrors.length > 0 || undefined"
      :aria-describedby="astErrors.length > 0 ? validationId : undefined"
      @click="open = !open"
    >
      <CmkMultitoneIcon
        :name="open ? 'chevron-down' : 'chevron-right'"
        primary-color="font"
        size="small"
        aria-hidden="true"
      />
      <span class="graphing-formula-form__value">{{ describeItem(item) }}</span>
    </button>

    <CmkInlineValidation v-if="astErrors.length > 0" :id="validationId" :validation="astErrors" />

    <CmkCollapsible :open="open">
      <div class="graphing-formula-form__listing">
        <template v-if="referencedItems.length > 0">
          <template v-for="referenced in referencedItems" :key="referenced.id">
            <ItemIdChip :id="referenced.id" :color="chipColor(referenced)" />
            <span class="graphing-formula-form__desc">{{
              isValid(referenced) ? describeItem(referenced) : _t('incomplete source')
            }}</span>
          </template>
        </template>
        <span v-else class="graphing-formula-form__empty">
          {{ _t('This formula references no sources.') }}
        </span>
      </div>
    </CmkCollapsible>
  </div>
</template>

<style scoped>
.graphing-formula-form {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);

  --graphing-formula-form-border: var(--color-mid-grey-10);
}

body[data-theme='modern-dark'] .graphing-formula-form {
  --graphing-formula-form-border: var(--color-mid-grey-90);
}

.graphing-formula-form__trigger {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-3);
  margin: 0;
  padding: 0;
  background: none;
  border: none;
  color: var(--font-color);
  cursor: pointer;

  &:focus-visible {
    outline: revert;
  }
}

.graphing-formula-form__listing {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: var(--dimension-4) var(--dimension-5);
  align-items: center;
  padding: var(--dimension-7);
  border: 1px solid var(--graphing-formula-form-border);
  border-radius: var(--border-radius);
}

.graphing-formula-form__desc {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.graphing-formula-form__empty {
  opacity: 0.6;
  font-style: italic;
}
</style>
