<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<!--
A compact pill stating why a graph has nothing to show, optionally offering a retry.

Layout-neutral: the host positions it, since the box it is centred in differs per surface.

The geometry follows dashboard/components/StatusMessage.vue, which is already this shape. The
colours are fixed rather than theme-derived: the design shows the same dark pill on both canvases.
-->

<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import CmkSpace from 'cmk-ui-library/components/CmkSpace.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

export type GraphNoticeVariant = 'error' | 'loading' | 'info'

const { _t } = usei18n()

// Plain strings rather than TranslatedString, as CmkAlertBox's `heading` is: a failure text often
// arrives already translated, from the fetch response's own `errors`.
const props = defineProps<{
  variant: GraphNoticeVariant
  message: string
  // Secondary detail: the next-step hint for an empty state, the technical cause for a failure.
  description?: string | undefined
  retry?: boolean | undefined
  // Lets a host repeating one notice over several graphs announce it once itself. Not
  // `aria-hidden`, which would take the retry inside out of reach.
  silent?: boolean | undefined
}>()

defineEmits<{ retry: [] }>()

const role = computed(() => {
  if (props.silent) {
    return undefined
  }
  return props.variant === 'error' ? 'alert' : 'status'
})

// `v-else` in the template does not narrow `loading` out of `variant`, so resolve the name here.
const multitoneIconName = computed<'error' | 'info'>(() =>
  props.variant === 'info' ? 'info' : 'error'
)

const ICON_COLOR = { custom: 'var(--color-white-100)' }
</script>

<template>
  <div class="graphing-graph-notice" :class="`graphing-graph-notice--${variant}`" :role="role">
    <CmkIcon
      v-if="variant === 'loading'"
      name="load-graph"
      size="medium"
      class="graphing-graph-notice__icon"
    />
    <CmkMultitoneIcon
      v-else
      :name="multitoneIconName"
      :primary-color="ICON_COLOR"
      size="medium"
      class="graphing-graph-notice__icon"
    />
    <div class="graphing-graph-notice__text">
      <span class="graphing-graph-notice__message">
        {{ message }}
        <template v-if="retry">
          <CmkSpace size="small" />
          <button type="button" class="graphing-graph-notice__retry" @click="$emit('retry')">
            {{ _t('Retry') }}
          </button>
        </template>
      </span>
      <span v-if="description" class="graphing-graph-notice__description">{{ description }}</span>
    </div>
  </div>
</template>

<style scoped>
.graphing-graph-notice {
  display: flex;
  align-items: flex-start;
  gap: var(--dimension-4);
  padding: var(--dimension-4) var(--dimension-6);
  border-radius: var(--dimension-3);
  font-size: var(--font-size-normal);
  color: var(--color-white-100);
}

.graphing-graph-notice--error {
  background-color: var(--color-dark-red-100);
}

.graphing-graph-notice--loading,
.graphing-graph-notice--info {
  background-color: var(--color-midnight-grey-50);
}

.graphing-graph-notice__icon {
  flex-shrink: 0;
}

.graphing-graph-notice__text {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
  min-width: 0;
}

/* Not scoped to `--info`: the single-line variants read the same either way. */
.graphing-graph-notice__message {
  font-weight: var(--font-weight-bold);
}

.graphing-graph-notice__description {
  color: var(--color-mid-grey-0);
}

/* An inline link rather than a CmkButton: the design puts the action at the end of the sentence. */
.graphing-graph-notice__retry {
  padding: 0;
  background: none;
  border: none;
  font: inherit;
  color: inherit;
  text-decoration: underline;
  cursor: pointer;
}
</style>
