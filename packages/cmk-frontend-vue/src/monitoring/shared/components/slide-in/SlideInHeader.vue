<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkLink from 'cmk-ui-library/components/CmkLink.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'

import type { HostMode, ServiceMode } from '@/monitoring/shared/api/types'
import IconList from '@/monitoring/shared/components/IconList.vue'
import ActionButtons, {
  type CellAction
} from '@/monitoring/shared/components/cell/ActionButtons.vue'
import { MODE_ICONS_PER_ROW } from '@/monitoring/shared/components/modeColumn'

withDefaults(
  defineProps<{
    title: string
    titleUrl?: string | undefined
    modes?: (HostMode | ServiceMode)[]
    actions?: CellAction[]
    loadActionMenu?: (() => Promise<CellAction[]>) | undefined
  }>(),
  { titleUrl: undefined, modes: () => [], actions: () => [], loadActionMenu: undefined }
)

const emit = defineEmits<{
  (event: 'select', action: CellAction): void
}>()
</script>

<template>
  <div class="monitoring-slide-in-header">
    <slot name="state" />
    <template v-if="modes.length">
      <span class="monitoring-slide-in-header__divider" aria-hidden="true" />
      <IconList :icons="modes" :max-per-row="MODE_ICONS_PER_ROW" />
      <span class="monitoring-slide-in-header__divider" aria-hidden="true" />
    </template>
    <CmkHeading type="h2" class="monitoring-slide-in-header__title">
      <CmkLink v-if="titleUrl" :href="titleUrl">{{ title }}</CmkLink>
      <template v-else>{{ title }}</template>
    </CmkHeading>
    <ActionButtons
      v-if="loadActionMenu || actions.length > 0"
      class="monitoring-slide-in-header__actions"
      :actions="actions"
      :max-visible="actions.length"
      :load="loadActionMenu"
      @select="emit('select', $event)"
    />
  </div>
</template>

<style scoped>
.monitoring-slide-in-header {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: var(--spacing);
}

.monitoring-slide-in-header__divider {
  flex: 0 0 auto;
  width: var(--dimension-2);
  height: var(--dimension-6);
  background: var(--ux-theme-6);
}

.monitoring-slide-in-header__title {
  margin: 0;
}

.monitoring-slide-in-header__actions {
  --monitoring-action-buttons-gap: var(--dimension-4);
  --monitoring-action-buttons-more-icon-width: var(--dimension-3);
  --monitoring-action-buttons-more-icon-height: var(--dimension-5);

  margin-left: auto;
}
</style>
