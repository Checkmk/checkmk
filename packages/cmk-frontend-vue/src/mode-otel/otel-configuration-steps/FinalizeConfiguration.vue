<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
export type FinalizeState = 'idle' | 'running' | 'success' | 'error'

export type ItemState = 'pending' | 'running' | 'success' | 'error'

export interface ActionItemStatus {
  key: string
  label: string
  state: ItemState
  error?: { title: string; detail: string }
}
</script>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import usei18n from '@/lib/i18n'

import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkIcon from '@/components/CmkIcon'
import CmkLoading from '@/components/CmkLoading.vue'

import type { PostSaveAction, PostSaveContext } from './post_save_actions.ts'

const props = defineProps<{
  siteId: string | null
  configName: string
  /**
   * Ordered list of post-save actions to run when the user clicks finish.
   * The caller composes this list (per-run create action + shared
   * `POST_SAVE_ACTIONS`, with edition-specific filtering applied) — this
   * component is purely the renderer and sequential runner.
   */
  actions: readonly PostSaveAction[]
  /**
   * Status alert texts. Default to OpenTelemetry wording so existing callers
   * stay unchanged; other QuickSetup flavors (e.g. Prometheus) pass their
   * own translated strings.
   */
  runningMessage?: string
  successMessage?: string
  errorHeading?: string
}>()

const emit = defineEmits<{
  (e: 'update:state', value: FinalizeState): void
}>()

const { _t } = usei18n()

const state = ref<FinalizeState>('idle')
const items = ref<ActionItemStatus[]>([])

// Keep the rendered checklist in sync with `actions`. Wizards build their
// per-run create-config action from refs that are still empty when this
// component mounts (e.g. siteId/port are filled in earlier steps), so the
// computed list grows after mount — a one-time snapshot at setup would
// render a stale list until `runActions` reset it on save.
watch(
  () => props.actions,
  (next) => {
    if (state.value === 'running') {
      return
    }
    items.value = next.map((a) => ({ key: a.key, label: a.label(), state: 'pending' }))
  },
  { immediate: true }
)

/**
 * Runs all post-save actions sequentially. Stops on first error so the
 * user sees exactly which change failed. Returns true if every action
 * succeeded.
 *
 * Exposed to the parent wizard so the save button in the #actions slot
 * can drive this component's state machine.
 */
async function runActions(): Promise<boolean> {
  if (!props.siteId || !props.configName) {
    // Should never happen in practice — site and config name are set in Step 1
    // and cannot be unset — but guard anyway so a misuse of the component
    // surfaces a clean error state instead of a TypeError.
    state.value = 'error'
    items.value = items.value.map((item, idx) =>
      idx === 0
        ? {
            ...item,
            state: 'error',
            error: {
              title: _t('Missing site selection'),
              detail: _t('Cannot apply configuration without a selected site.')
            }
          }
        : item
    )
    return false
  }

  state.value = 'running'
  const ctx: PostSaveContext = { siteId: props.siteId, configName: props.configName }

  // Reset any previous run state so retries start clean.
  items.value = props.actions.map((a) => ({
    key: a.key,
    label: a.label(),
    state: 'pending'
  }))

  for (let i = 0; i < props.actions.length; i++) {
    const action = props.actions[i]!
    items.value[i]!.state = 'running'
    const result = await action.execute(ctx)
    if (result.ok) {
      items.value[i]!.state = 'success'
      continue
    }
    items.value[i]!.state = 'error'
    items.value[i]!.error = result.error
    state.value = 'error'
    return false
  }

  state.value = 'success'
  return true
}

const firstError = computed(() => items.value.find((i) => i.state === 'error')?.error)

const runningText = computed(
  () => props.runningMessage ?? _t('Verifying the OpenTelemetry configuration...')
)
const successText = computed(
  () => props.successMessage ?? _t('OpenTelemetry configuration saved successfully.')
)
const errorHeadingText = computed(
  () => props.errorHeading ?? _t('Could not save the OpenTelemetry configuration')
)

// Propagate state transitions to the parent so it can update the save
// button's label / disabled binding. `immediate: true` emits the initial
// 'idle' state so the parent does not have to hard-code a default.
watch(state, (value) => emit('update:state', value), { immediate: true })

defineExpose({ runActions })
</script>

<template>
  <div class="mode-otel-finalize-configuration">
    <ul class="mode-otel-finalize-configuration__items">
      <li
        v-for="item in items"
        :key="item.key"
        class="mode-otel-finalize-configuration__item"
        :class="`mode-otel-finalize-configuration__item--${item.state}`"
      >
        <span class="mode-otel-finalize-configuration__item-icon">
          <CmkIcon v-if="item.state === 'success'" name="check" size="small" variant="inline" />
          <CmkIcon v-else-if="item.state === 'error'" name="error" size="small" variant="inline" />
          <CmkLoading v-else-if="item.state === 'running'" height="6px" />
          <span v-else class="mode-otel-finalize-configuration__item-bullet" />
        </span>
        <span class="mode-otel-finalize-configuration__item-label">{{ item.label }}</span>
      </li>
    </ul>

    <CmkAlertBox v-if="state === 'running'" variant="loading" size="small">
      {{ runningText }}
    </CmkAlertBox>
    <template v-else-if="state === 'success'">
      <CmkAlertBox variant="success" size="small">
        {{ successText }}
      </CmkAlertBox>
      <slot name="success-summary" />
    </template>
    <CmkAlertBox
      v-else-if="state === 'error'"
      variant="error"
      size="small"
      :heading="firstError?.title ?? errorHeadingText"
    >
      {{ firstError?.detail ?? _t('An unexpected error occurred. Please try again.') }}
    </CmkAlertBox>
  </div>
</template>

<style scoped>
.mode-otel-finalize-configuration {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

.mode-otel-finalize-configuration__intro {
  margin: 0;
}

.mode-otel-finalize-configuration__items {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
}

.mode-otel-finalize-configuration__item {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
}

.mode-otel-finalize-configuration__item--success {
  color: var(--success-dimmed);
}

.mode-otel-finalize-configuration__item--error {
  color: var(--color-danger);
}

.mode-otel-finalize-configuration__item-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
}

.mode-otel-finalize-configuration__item-bullet {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: var(--font-color);
  opacity: 0.4;
}
</style>
