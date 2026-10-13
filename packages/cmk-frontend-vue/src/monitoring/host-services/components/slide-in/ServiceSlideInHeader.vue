<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import type { HostServiceEntry } from '@/monitoring/shared/api/types'

export type ServiceHeaderSubject = Pick<
  HostServiceEntry,
  'name' | 'state' | 'stale' | 'is_flapping' | 'modes'
>
</script>

<script setup lang="ts">
import ServiceStateDisplay from '@/monitoring/shared/components/ServiceStateDisplay.vue'
import StateModeIcons from '@/monitoring/shared/components/StateModeIcons.vue'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionButtons.vue'
import SlideInHeader from '@/monitoring/shared/components/slide-in/SlideInHeader.vue'

withDefaults(
  defineProps<{
    service: ServiceHeaderSubject
    actions?: CellAction[]
    loadActionMenu?: (() => Promise<CellAction[]>) | undefined
  }>(),
  { actions: () => [], loadActionMenu: undefined }
)
</script>

<template>
  <SlideInHeader
    :title="service.name"
    :modes="service.modes ?? []"
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
