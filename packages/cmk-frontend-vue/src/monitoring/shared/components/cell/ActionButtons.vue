<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkAlertBox from 'cmk-ui-library/components/CmkAlertBox.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton/CmkButton.vue'
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import CmkSkeleton from 'cmk-ui-library/components/CmkSkeleton.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import {
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuPortal,
  DropdownMenuRoot,
  DropdownMenuTrigger
} from 'reka-ui'
import { computed, ref } from 'vue'

import ActionIcon, { type ActionIcon as ActionIconSpec } from './ActionIcon.vue'

export interface CellAction {
  id: string
  label: TranslatedString
  icon: ActionIconSpec
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
  }>(),
  { maxVisible: 2, load: undefined }
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
  // A link navigates on its own; only a command is something for the parent to run.
  if (action.disabled || action.url) {
    return
  }
  emit('select', action)
}
</script>

<template>
  <div class="monitoring-action-buttons">
    <CmkButton
      v-for="action in visibleActions"
      :key="action.id"
      variant="optional"
      size="iconOnly"
      :href="action.url"
      :target="action.url ? (action.target ?? '_top') : undefined"
      :title="action.label"
      :aria-label="action.label"
      :disabled="action.disabled"
      @click="select(action)"
    >
      <ActionIcon :icon="action.icon" />
    </CmkButton>

    <DropdownMenuRoot v-if="hasMenu" @update:open="onOpenChange">
      <DropdownMenuTrigger as-child>
        <CmkIconButton
          name="more-actions"
          primary-color="font"
          size="small"
          :title="_t('More actions')"
          :aria-label="_t('More actions')"
        />
      </DropdownMenuTrigger>
      <DropdownMenuPortal>
        <DropdownMenuContent
          class="cmk-vue-app monitoring-action-buttons__menu"
          align="end"
          :side-offset="4"
        >
          <template v-for="action in overflowActions" :key="action.id">
            <DropdownMenuItem
              v-if="action.url"
              as-child
              class="monitoring-action-buttons__menu-item"
            >
              <a :href="action.url" :target="action.target ?? '_top'">
                <ActionIcon :icon="action.icon" />
                <span class="monitoring-action-buttons__menu-label">{{ action.label }}</span>
              </a>
            </DropdownMenuItem>
            <DropdownMenuItem
              v-else
              class="monitoring-action-buttons__menu-item"
              :disabled="action.disabled === true"
              @select="select(action)"
            >
              <ActionIcon :icon="action.icon" />
              <span class="monitoring-action-buttons__menu-label">{{ action.label }}</span>
            </DropdownMenuItem>
          </template>

          <template v-if="load">
            <div
              v-if="loading && loadedActions === null"
              class="monitoring-action-buttons__menu-status"
            >
              <CmkSkeleton type="text" />
              <CmkSkeleton type="text" />
              <CmkSkeleton type="text" />
            </div>
            <CmkAlertBox
              v-else-if="failed && loadedActions === null && !overflowActions.length"
              variant="error"
              size="small"
              class="monitoring-action-buttons__menu-status"
            >
              {{ _t('Could not load actions.') }}
            </CmkAlertBox>
            <div
              v-else-if="failed && loadedActions === null"
              class="monitoring-action-buttons__menu-status monitoring-action-buttons__menu-hint"
            >
              {{ _t('Could not load more actions.') }}
            </div>
            <div
              v-else-if="!overflowActions.length && loadedActions && !loadedActions.length"
              class="monitoring-action-buttons__menu-status monitoring-action-buttons__menu-hint"
            >
              {{ _t('No actions available') }}
            </div>
            <template v-for="action in loadedActions ?? []" :key="action.id">
              <DropdownMenuItem
                v-if="action.url"
                as-child
                class="monitoring-action-buttons__menu-item"
              >
                <a :href="action.url" :target="action.target ?? '_top'">
                  <ActionIcon :icon="action.icon" />
                  <span class="monitoring-action-buttons__menu-label">{{ action.label }}</span>
                </a>
              </DropdownMenuItem>
              <DropdownMenuItem
                v-else
                class="monitoring-action-buttons__menu-item"
                :disabled="action.disabled === true"
                @select="select(action)"
              >
                <ActionIcon :icon="action.icon" />
                <span class="monitoring-action-buttons__menu-label">{{ action.label }}</span>
              </DropdownMenuItem>
            </template>
          </template>
        </DropdownMenuContent>
      </DropdownMenuPortal>
    </DropdownMenuRoot>
  </div>
</template>

<style scoped>
.monitoring-action-buttons {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: var(--dimension-2);
}
</style>

<style>
/* stylelint-disable checkmk/vue-bem-naming-convention */
.monitoring-action-buttons__menu {
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

.monitoring-action-buttons__menu-item {
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

.monitoring-action-buttons__menu-status {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
  padding: var(--dimension-3) var(--dimension-4);
}

.monitoring-action-buttons__menu-hint {
  color: var(--font-color-dimmed);
  white-space: nowrap;
}

.monitoring-action-buttons__menu-label {
  white-space: nowrap;
}
</style>
