<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { HostServiceEntry, ServiceMode } from '@/monitoring/shared/api/types'
import ServiceStateDisplay from '@/monitoring/shared/components/ServiceStateDisplay.vue'
import StateModeIcons from '@/monitoring/shared/components/StateModeIcons.vue'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionButtons.vue'
import SlideInHeader from '@/monitoring/shared/components/slide-in/SlideInHeader.vue'

withDefaults(
  defineProps<{
    service: HostServiceEntry
    // The modes and actions only arrive with the overview, so the header renders without them
    // until it loads.
    modes?: ServiceMode[]
    actions?: CellAction[]
    loadActionMenu?: (() => Promise<CellAction[]>) | undefined
  }>(),
  { modes: () => [], actions: () => [], loadActionMenu: undefined }
)
</script>

<template>
  <SlideInHeader
    :title="service.name"
    :modes="modes"
    :actions="actions"
    :load-action-menu="loadActionMenu"
  >
    <template #state>
      <span class="monitoring-service-slide-in-header__state">
        <ServiceStateDisplay :state="service.state" :stale="service.stale" />
        <StateModeIcons :flapping="service.is_flapping" :stale="service.stale" />
      </span>
    </template>
  </SlideInHeader>
</template>

<style scoped>
.monitoring-service-slide-in-header__state {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-3);
}
</style>
