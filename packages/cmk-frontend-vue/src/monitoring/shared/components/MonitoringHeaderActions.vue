<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { provideTeleportPlacement } from '@/monitoring/shared/components/teleportPlacement'

const props = defineProps<{ teleportTarget?: string | null | undefined }>()

const { target, isDefault } = provideTeleportPlacement('.titlebar', () => props.teleportTarget)
</script>

<template>
  <Teleport defer :to="target">
    <div
      class="monitoring-header-actions"
      :class="
        isDefault ? 'monitoring-header-actions--titlebar' : 'monitoring-header-actions--page-menu'
      "
    >
      <slot />
    </div>
  </Teleport>
</template>

<style scoped>
.monitoring-header-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--dimension-6);
}

.monitoring-header-actions--titlebar {
  align-self: center;
  margin-right: var(--dimension-6);
}

.monitoring-header-actions--page-menu {
  height: 100%;
  margin-right: var(--dimension-3);
}
</style>
