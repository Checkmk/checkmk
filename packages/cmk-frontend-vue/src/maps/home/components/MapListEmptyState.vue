<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
What the list says when there is nothing in it — a site without maps yet, or a
search that matched none. Follows the monitoring empty state: a sentence about
what happened and one about what to do next.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import { useAuth } from '@/maps/services/context'

const props = defineProps<{ searchQuery: string }>()

const { _t } = usei18n()
const auth = useAuth()

const title = computed(() =>
  props.searchQuery
    ? _t('No maps match "%{q}".', { q: props.searchQuery })
    : _t('No maps configured.')
)

const hint = computed(() => {
  if (props.searchQuery) {
    return _t('Check for typing errors or try a broader term.')
  }
  return auth.canCreateMaps.value
    ? _t('Create your first map with "Add map" above.')
    : _t('Contact your administrator to have a map created.')
})
</script>

<template>
  <div class="maps-map-list-empty-state" aria-live="polite">
    <p class="maps-map-list-empty-state__title">{{ title }}</p>
    <p class="maps-map-list-empty-state__hint">{{ hint }}</p>
  </div>
</template>

<style scoped>
.maps-map-list-empty-state {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-half);
  padding: var(--dimension-10) 0;
  text-align: center;
}

.maps-map-list-empty-state__title {
  margin: 0;
  font-weight: var(--font-weight-bold);
}

.maps-map-list-empty-state__hint {
  margin: 0;
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
}
</style>
