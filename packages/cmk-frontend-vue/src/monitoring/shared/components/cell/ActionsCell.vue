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
import { computed, ref } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkButton from '@/components/CmkButton/CmkButton.vue'
import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'
import CmkMultitoneIcon from '@/components/CmkIcon/CmkMultitoneIcon.vue'
import type { SimpleIcons } from '@/components/CmkIcon/types'
import CmkSkeleton from '@/components/CmkSkeleton.vue'

import BaseCell, { type CellVerticalAlign } from './BaseCell.vue'

export interface CellAction {
  id: string
  label: TranslatedString
  icon: SimpleIcons
  disabled?: boolean | undefined
  // When set, the action is a link and is rendered as a native anchor; otherwise it is a button
  // that emits `select` for the parent to handle.
  url?: string | undefined
  target?: string | undefined
}

const props = withDefaults(
  defineProps<{
    actions: CellAction[]
    maxVisible?: number
    // Optional lazy loader for additional overflow-menu entries, fetched when the menu is opened.
    load?: (() => Promise<CellAction[]>) | undefined
    columnId?: string | undefined
    verticalAlign?: CellVerticalAlign | undefined
  }>(),
  { maxVisible: 2, load: undefined, columnId: undefined, verticalAlign: undefined }
)

const emit = defineEmits<{
  (event: 'select', action: CellAction): void
}>()

const { _t } = usei18n()

const visibleActions = computed(() => props.actions.slice(0, Math.max(0, props.maxVisible)))
const overflowActions = computed(() => props.actions.slice(Math.max(0, props.maxVisible)))
const hasMenu = computed(() => overflowActions.value.length > 0 || props.load !== undefined)

const loadedActions = ref<CellAction[] | null>(null)
const loading = ref(false)
const failed = ref(false)

async function fetchLoaded(): Promise<void> {
  if (!props.load) {
    return
  }
  loading.value = true
  failed.value = false
  try {
    loadedActions.value = await props.load()
  } catch {
    failed.value = true
  } finally {
    loading.value = false
  }
}

function onOpenChange(open: boolean): void {
  // Fetch on every open (like the legacy menu); previously loaded entries stay visible until the
  // refresh so reopening is flicker free and reflects the current host state.
  if (open && props.load && !loading.value) {
    void fetchLoaded()
  }
}

function select(action: CellAction): void {
  if (action.disabled) {
    return
  }
  emit('select', action)
}
</script>

<template>
  <BaseCell :column-id="columnId" :vertical-align="verticalAlign">
    <template #default>
      <div class="monitoring-actions-cell__actions">
        <template v-for="action in visibleActions" :key="action.id">
          <a
            v-if="action.url"
            class="monitoring-actions-cell__icon-button"
            :href="action.url"
            :target="action.target ?? 'main'"
            :title="action.label"
            :aria-label="action.label"
          >
            <CmkIcon :name="action.icon" size="small" />
          </a>
          <CmkButton
            v-else
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
        </template>

        <DropdownMenuRoot v-if="hasMenu" @update:open="onOpenChange">
          <DropdownMenuTrigger
            class="monitoring-actions-cell__icon-button"
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
              <template v-for="action in overflowActions" :key="action.id">
                <DropdownMenuItem
                  v-if="action.url"
                  as-child
                  class="monitoring-actions-cell__menu-item"
                >
                  <a :href="action.url" :target="action.target ?? 'main'">
                    <CmkIcon :name="action.icon" size="small" />
                    <span class="monitoring-actions-cell__menu-label">{{ action.label }}</span>
                  </a>
                </DropdownMenuItem>
                <DropdownMenuItem
                  v-else
                  class="monitoring-actions-cell__menu-item"
                  :disabled="action.disabled === true"
                  @select="select(action)"
                >
                  <CmkIcon :name="action.icon" size="small" />
                  <span class="monitoring-actions-cell__menu-label">{{ action.label }}</span>
                </DropdownMenuItem>
              </template>

              <template v-if="load">
                <div
                  v-if="loading && loadedActions === null"
                  class="monitoring-actions-cell__menu-status"
                >
                  <CmkSkeleton type="text" />
                  <CmkSkeleton type="text" />
                  <CmkSkeleton type="text" />
                </div>
                <CmkAlertBox
                  v-else-if="failed && loadedActions === null && !overflowActions.length"
                  variant="error"
                  size="small"
                  class="monitoring-actions-cell__menu-status"
                >
                  {{ _t('Could not load actions.') }}
                </CmkAlertBox>
                <div
                  v-else-if="failed && loadedActions === null"
                  class="monitoring-actions-cell__menu-status monitoring-actions-cell__menu-hint"
                >
                  {{ _t('Could not load more actions.') }}
                </div>
                <div
                  v-else-if="!overflowActions.length && loadedActions && !loadedActions.length"
                  class="monitoring-actions-cell__menu-status monitoring-actions-cell__menu-hint"
                >
                  {{ _t('No actions available') }}
                </div>
                <template v-for="action in loadedActions ?? []" :key="action.id">
                  <DropdownMenuItem
                    v-if="action.url"
                    as-child
                    class="monitoring-actions-cell__menu-item"
                  >
                    <a :href="action.url" :target="action.target ?? 'main'">
                      <CmkIcon :name="action.icon" size="small" />
                      <span class="monitoring-actions-cell__menu-label">{{ action.label }}</span>
                    </a>
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    v-else
                    class="monitoring-actions-cell__menu-item"
                    :disabled="action.disabled === true"
                    @select="select(action)"
                  >
                    <CmkIcon :name="action.icon" size="small" />
                    <span class="monitoring-actions-cell__menu-label">{{ action.label }}</span>
                  </DropdownMenuItem>
                </template>
              </template>
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
  margin-top: var(--dimension-2);
}

.monitoring-actions-cell__button {
  flex: 0 0 auto;
}

.monitoring-actions-cell__icon-button {
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
  text-decoration: none;

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
  min-width: 200px;
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
  color: inherit;
  text-decoration: none;
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

.monitoring-actions-cell__menu-status {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
  padding: var(--dimension-3) var(--dimension-4);
}

.monitoring-actions-cell__menu-hint {
  color: var(--font-color-dimmed);
  white-space: nowrap;
}

.monitoring-actions-cell__menu-label {
  white-space: nowrap;
}
</style>
