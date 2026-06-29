<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import {
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuPortal,
  DropdownMenuRoot,
  DropdownMenuTrigger
} from 'reka-ui'
import { computed } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkButton from '@/components/CmkButton/CmkButton.vue'
import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'
import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'
import type { SimpleIcons } from '@/components/CmkIcon/types'

import BaseCell from './BaseCell.vue'

export interface CellAction {
  id: string
  label: TranslatedString
  icon: SimpleIcons
  disabled?: boolean | undefined
}

const props = withDefaults(
  defineProps<{
    actions: CellAction[]
    maxVisible?: number
    columnId?: string | undefined
  }>(),
  { maxVisible: 2, columnId: undefined }
)

const emit = defineEmits<{
  (event: 'select', action: CellAction): void
}>()

const { _t } = usei18n()

const visibleActions = computed(() => props.actions.slice(0, Math.max(0, props.maxVisible)))
const overflowActions = computed(() => props.actions.slice(Math.max(0, props.maxVisible)))
const hasOverflow = computed(() => overflowActions.value.length > 0)

function select(action: CellAction): void {
  if (action.disabled) {
    return
  }
  emit('select', action)
}
</script>

<template>
  <BaseCell class="monitoring-actions-cell" :column-id="columnId">
    <template #default>
      <div class="monitoring-actions-cell__actions">
        <CmkButton
          v-for="action in visibleActions"
          :key="action.id"
          size="iconOnly"
          variant="optional"
          :title="action.label"
          :aria-label="action.label"
          :disabled="action.disabled"
          class="monitoring-actions-cell__button"
          @click="select(action)"
        >
          <CmkIcon :name="action.icon" size="small" />
        </CmkButton>

        <DropdownMenuRoot v-if="hasOverflow">
          <DropdownMenuTrigger
            class="monitoring-actions-cell__more"
            :title="_t('More actions')"
            :aria-label="_t('More actions')"
          >
            <CmkMultitoneIcon name="more-actions" primary-color="font" size="small" />
          </DropdownMenuTrigger>
          <DropdownMenuPortal>
            <DropdownMenuContent
              class="cmk-vue-app monitoring-actions-cell__menu"
              align="end"
              :side-offset="4"
            >
              <DropdownMenuItem
                v-for="action in overflowActions"
                :key="action.id"
                class="monitoring-actions-cell__menu-item"
                :disabled="action.disabled === true"
                @select="select(action)"
              >
                <CmkIcon :name="action.icon" size="small" />
                <span class="monitoring-actions-cell__menu-label">{{ action.label }}</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenuPortal>
        </DropdownMenuRoot>
      </div>
    </template>
  </BaseCell>
</template>

<style scoped>
.monitoring-actions-cell__actions {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: var(--dimension-2);
}

.monitoring-actions-cell__button {
  flex: 0 0 auto;
}

.monitoring-actions-cell__more {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  padding: var(--dimension-2);
  margin: 0;
  background: transparent;
  border: none;
  border-radius: var(--dimension-2);
  cursor: pointer;
  color: inherit;

  &:hover {
    background-color: var(--ux-theme-3);
  }

  &:focus-visible {
    outline: 1px solid var(--success);
    outline-offset: 1px;
  }
}
</style>

<style>
/* stylelint-disable checkmk/vue-bem-naming-convention */
.monitoring-actions-cell__menu {
  display: flex;
  flex-direction: column;
  min-width: 180px;
  padding: var(--dimension-2);
  background: var(--ux-theme-1);
  border: 1px solid var(--ux-theme-6);
  border-radius: var(--border-radius);
  box-shadow: 0 2px 8px rgb(0 0 0 / 30%);
  z-index: var(--z-index-modal);
}

.monitoring-actions-cell__menu-item {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  padding: var(--dimension-3) var(--dimension-4);
  border-radius: var(--dimension-2);
  cursor: pointer;
  outline: none;
  user-select: none;

  &[data-highlighted] {
    background-color: var(--ux-theme-3);
  }

  &[data-disabled] {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.monitoring-actions-cell__menu-label {
  white-space: nowrap;
}
</style>
