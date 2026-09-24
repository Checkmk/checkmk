<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import CmkSpace from 'cmk-ui-library/components/CmkSpace.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

export type CmkSurfaceNoticeVariant = 'error' | 'warning' | 'loading' | 'info'

export interface CmkSurfaceNoticeProps {
  variant: CmkSurfaceNoticeVariant
  message: string
  description?: string | undefined
  retry?: boolean | undefined
  // Not `aria-hidden`: that would take the retry inside out of reach.
  silent?: boolean | undefined
}

const { _t } = usei18n()

const props = defineProps<CmkSurfaceNoticeProps>()

defineEmits<{ retry: [] }>()

const role = computed(() => {
  if (props.silent) {
    return undefined
  }
  return props.variant === 'error' ? 'alert' : 'status'
})

const multitoneIconName = computed<'error' | 'warning'>(() =>
  props.variant === 'warning' ? 'warning' : 'error'
)

const iconColor = computed(() => ({
  custom: `var(--cmk-alert-box-${props.variant}-icon-color)`
}))
</script>

<template>
  <div class="cmk-surface-notice" :class="`cmk-surface-notice--${variant}`" :role="role">
    <CmkIcon
      v-if="variant === 'loading'"
      name="load-graph"
      size="medium"
      class="cmk-surface-notice__icon"
    />
    <CmkIcon
      v-else-if="variant === 'info'"
      name="graph"
      size="xxlarge"
      class="cmk-surface-notice__icon"
    />
    <CmkMultitoneIcon
      v-else
      :name="multitoneIconName"
      :primary-color="iconColor"
      size="medium"
      class="cmk-surface-notice__icon"
    />
    <div class="cmk-surface-notice__text">
      <span class="cmk-surface-notice__message">
        {{ message }}
        <template v-if="retry">
          <CmkSpace size="small" />
          <button type="button" class="cmk-surface-notice__retry" @click="$emit('retry')">
            {{ _t('Retry') }}
          </button>
        </template>
      </span>
      <span v-if="description" class="cmk-surface-notice__description">{{ description }}</span>
    </div>
  </div>
</template>

<style scoped>
.cmk-surface-notice {
  /* It sits over a plot the user can still pan, and over an inert one whose retry must still
     be reachable, so only the retry takes the pointer. */
  pointer-events: none;
  display: flex;
  align-items: flex-start;
  gap: var(--dimension-4);
  padding: var(--dimension-4) var(--dimension-6);
  border-radius: var(--dimension-3);
  font-size: var(--font-size-normal);
  color: var(--font-color);
}

.cmk-surface-notice--error {
  background-color: var(--cmk-alert-box-error-bg-color);
}

.cmk-surface-notice--warning {
  background-color: var(--cmk-alert-box-warning-bg-color);
}

.cmk-surface-notice--info {
  background-color: var(--cmk-alert-box-info-bg-color);
}

.cmk-surface-notice--loading {
  background-color: var(--cmk-alert-box-loading-bg-color);
}

.cmk-surface-notice__icon {
  flex-shrink: 0;
}

.cmk-surface-notice__text {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
  min-width: 0;
}

.cmk-surface-notice__message {
  font-weight: var(--font-weight-bold);
}

.cmk-surface-notice__description {
  color: var(--cmk-alert-box-text-color);
}

/* An inline link rather than a CmkButton: the design puts the action at the end of the sentence. */
.cmk-surface-notice__retry {
  pointer-events: auto;
  padding: 0;
  background: none;
  border: none;
  font: inherit;
  color: inherit;
  text-decoration: underline;
  cursor: pointer;
}
</style>
