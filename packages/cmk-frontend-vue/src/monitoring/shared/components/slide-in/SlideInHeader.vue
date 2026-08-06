<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'

import type { HostMode, ServiceMode } from '@/monitoring/shared/api/types'
import ModeIcons from '@/monitoring/shared/components/ModeIcons.vue'
import ActionButtons, {
  type CellAction
} from '@/monitoring/shared/components/cell/ActionButtons.vue'

withDefaults(
  defineProps<{
    title: string
    modes?: (HostMode | ServiceMode)[]
    actions?: CellAction[]
    loadActionMenu?: (() => Promise<CellAction[]>) | undefined
  }>(),
  { modes: () => [], actions: () => [], loadActionMenu: undefined }
)

const emit = defineEmits<{
  (event: 'select', action: CellAction): void
}>()
</script>

<template>
  <div class="monitoring-slide-in-header">
    <slot name="state" />
    <ModeIcons v-if="modes.length" :modes="modes" />
    <CmkHeading type="h2" class="monitoring-slide-in-header__title">
      {{ title }}
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

.monitoring-slide-in-header__title {
  margin: 0;
}

.monitoring-slide-in-header__actions {
  margin-left: auto;
}
</style>
