<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

const { _t } = usei18n()

const props = withDefaults(
  defineProps<{
    hasSearchQuery?: boolean
    hasActiveFilter?: boolean
  }>(),
  { hasSearchQuery: false, hasActiveFilter: false }
)

const title = computed(() => {
  if (props.hasActiveFilter && props.hasSearchQuery) {
    return _t('No results for your combination of search and filter settings.')
  }
  if (props.hasActiveFilter) {
    return _t('No results found for your active filters.')
  }
  if (props.hasSearchQuery) {
    return _t('No results found for your search.')
  }
  return _t('No results found.')
})

const hint = computed(() => {
  if (props.hasActiveFilter && props.hasSearchQuery) {
    return _t('Adjust or clear search and filters to start fresh.')
  }
  if (props.hasSearchQuery) {
    return _t('Check for typing errors, try using wildcards or a broader term.')
  }
  if (props.hasActiveFilter) {
    return _t('Remove one or more filters to widen the result.')
  }
  return null
})
</script>

<template>
  <div class="monitoring-empty-state" aria-live="polite">
    <p class="monitoring-empty-state__title">{{ title }}</p>
    <p v-if="hint" class="monitoring-empty-state__hint">{{ hint }}</p>
  </div>
</template>

<style scoped>
.monitoring-empty-state {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-half);
  padding: var(--spacing) var(--spacing-half);
}

.monitoring-empty-state__title {
  margin: 0;
  font-weight: var(--font-weight-bold);
}

.monitoring-empty-state__hint {
  margin: 0;
  color: var(--font-color-dimmed);
  font-size: var(--font-size-small);
}
</style>
