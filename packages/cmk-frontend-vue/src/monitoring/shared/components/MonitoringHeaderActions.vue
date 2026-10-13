<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { onBeforeUnmount, watchEffect } from 'vue'

import { provideTeleportPlacement } from '@/monitoring/shared/components/teleportPlacement'

const props = defineProps<{ teleportTarget?: string | null | undefined }>()

const { target, isDefault } = provideTeleportPlacement(
  '.titlebar .titlebar-main',
  () => props.teleportTarget
)

/* The server-rendered title bar is only reflowed while this component puts its actions into it,
   so the global rules below must not leak to other pages sharing the stylesheet. */
const TITLEBAR_HOST_CLASS = 'monitoring-header-actions-host'

function setTitlebarHost(active: boolean): void {
  document.getElementById('top_heading')?.classList.toggle(TITLEBAR_HOST_CLASS, active)
}

watchEffect(() => setTitlebarHost(isDefault.value))
onBeforeUnmount(() => setTitlebarHost(false))
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
  /* Sits on the title row, below the breadcrumb, so the breadcrumb keeps the full width. Like the
     refresh timer it stays on the right and runs off the screen instead of covering the title. */
  margin-right: var(--dimension-3);
}

.monitoring-header-actions--page-menu {
  height: 100%;
  margin-right: var(--dimension-3);
}
</style>

<!-- The page title is rendered by the server and shares its row with the header actions. The
     title takes the space the actions leave and is truncated with an ellipsis (the legacy styles
     already set overflow and text-overflow), so the actions never leave the row, however narrow
     the content area gets (e.g. next to the sidebar). Applies only to #top_heading while it
     carries the host class, which is set when this component teleports into the title bar. -->
<style lang="scss">
#top_heading.monitoring-header-actions-host {
  .titlebar .titlebar-main {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: end;
    column-gap: var(--dimension-6);
    min-width: 0;

    /* The header actions collapse by the width of this row, not the viewport: the sidebar and the
       refresh timer take width from it. Its width comes from the flex layout of the title bar, so
       the containment cannot depend on the title. */
    container-type: inline-size;

    > .breadcrumb {
      grid-column: 1 / -1;
    }
  }

  a.title {
    max-width: 100%;
  }
}
</style>
