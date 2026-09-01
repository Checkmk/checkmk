<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import useId from 'cmk-ui-library/lib/useId'

import { useItemDescription } from '../../composables/useItemDescription'
import { type GraphItem, type ItemId, isSingleLine } from '../../types'
import ItemIdButton from './ItemIdButton.vue'

export interface SectionAlert {
  id: ItemId
  text: TranslatedString
  /** Changes per alert so the alert box remounts and restarts its auto-dismiss timer. */
  nonce: number
}

const { _t } = usei18n()

const headingId = useId()

const {
  heading,
  emptyText,
  items,
  actionLabel,
  itemBlockReason,
  showActions = false,
  alert = null
} = defineProps<{
  heading: TranslatedString
  emptyText: TranslatedString
  items: readonly GraphItem[]
  actionLabel: (id: ItemId) => TranslatedString
  itemBlockReason?: ((item: GraphItem) => TranslatedString | null) | undefined
  /** Render edit/delete actions on each row (calculations only). */
  showActions?: boolean
  /** Success alert shown inline in the matching row, just before the actions. */
  alert?: SectionAlert | null | undefined
}>()

const emit = defineEmits<{
  insertId: [id: ItemId]
  edit: [id: ItemId]
  delete: [id: ItemId]
  dismissAlert: []
}>()

const { describeItem } = useItemDescription()

function onAlertOpenChange(open: boolean): void {
  if (!open) {
    emit('dismissAlert')
  }
}
</script>

<template>
  <section class="graphing-item-list-section" :aria-labelledby="headingId">
    <CmkHeading :id="headingId" type="h4">{{ heading }}</CmkHeading>
    <p v-if="items.length === 0" class="graphing-item-list-section__empty">
      {{ emptyText }}
    </p>
    <ul v-else class="graphing-item-list-section__rows">
      <li v-for="item in items" :key="item.id" class="graphing-item-list-section__row">
        <ItemIdButton
          :id="item.id"
          :color="isSingleLine(item) ? item.color : undefined"
          :label="actionLabel(item.id)"
          :block-reason="itemBlockReason?.(item) ?? null"
          @click="emit('insertId', item.id)"
        />
        <span class="graphing-item-list-section__title">
          {{ describeItem(item) }}
        </span>
        <CmkAlertBox
          v-if="alert !== null && alert.id === item.id"
          :key="alert.nonce"
          class="graphing-item-list-section__alert"
          variant="success"
          size="small"
          auto-dismiss
          @update:open="onAlertOpenChange"
        >
          {{ alert.text }}
        </CmkAlertBox>
        <span v-if="showActions" class="graphing-item-list-section__actions">
          <CmkButton
            size="iconOnly"
            :title="_t('Edit')"
            :aria-label="_t('Edit %{id}', { id: item.id })"
            @click="emit('edit', item.id)"
          >
            <CmkIcon name="edit" size="small" />
          </CmkButton>
          <CmkButton
            size="iconOnly"
            :title="_t('Delete')"
            :aria-label="_t('Delete %{id}', { id: item.id })"
            @click="emit('delete', item.id)"
          >
            <CmkIcon name="delete" size="small" />
          </CmkButton>
        </span>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.graphing-item-list-section {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

.graphing-item-list-section__rows {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}

/* min-height matches the inline alert so it can appear and dismiss without layout shift. */
.graphing-item-list-section__row {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  min-height: var(--dimension-10);
}

.graphing-item-list-section__title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Narrow the alert box to row size. */
.graphing-item-list-section__alert {
  flex-shrink: 0;
  white-space: nowrap;
  margin: 0;
  padding: var(--dimension-2) var(--dimension-4);
  align-items: center;
}

.graphing-item-list-section__actions {
  display: inline-flex;
  flex-shrink: 0;
  gap: var(--dimension-3);
  margin-left: auto;
}

.graphing-item-list-section__empty {
  margin: 0;
  opacity: 0.6;
  font-style: italic;
}
</style>
