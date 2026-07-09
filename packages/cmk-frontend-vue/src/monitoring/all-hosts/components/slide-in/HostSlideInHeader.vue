<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

import type { HostEntry } from '@/monitoring/shared/api/types'
import HostStateDisplay from '@/monitoring/shared/components/HostStateDisplay.vue'

defineProps<{ host: HostEntry }>()
</script>

<template>
  <div class="monitoring-host-slide-in-header">
    <HostStateDisplay :state="host.state" />
    <CmkParagraph v-if="host.address" class="monitoring-host-slide-in-header__address">
      {{ host.address }}
    </CmkParagraph>
  </div>
</template>

<style scoped>
.monitoring-host-slide-in-header {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: var(--spacing);
}

.monitoring-host-slide-in-header__address {
  color: var(--font-color-dimmed);
}
</style>
