<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkHeading from '@/components/typography/CmkHeading.vue'

import type { HostEntry } from '@/monitoring/shared/api/types'
import HostStateDisplay from '@/monitoring/shared/components/HostStateDisplay.vue'

defineProps<{ host: HostEntry }>()
</script>

<template>
  <div class="monitoring-host-slide-in-header">
    <HostStateDisplay :state="host.state" />
    <CmkHeading type="h2" class="monitoring-host-slide-in-header__name">
      {{ host.name }}
    </CmkHeading>
  </div>
</template>

<style scoped>
.monitoring-host-slide-in-header {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: var(--spacing);
}

.monitoring-host-slide-in-header__name {
  margin: 0;
}
</style>
