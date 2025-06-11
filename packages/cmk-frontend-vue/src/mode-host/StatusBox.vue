<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkIcon from '@/components/CmkIcon.vue'

defineProps<{
  status: DNSStatus
}>()

export interface DNSStatus {
  tooltip: string
  status: 'loading' | 'ok' | 'warn' | 'crit'
}

function getIconName(status: DNSStatus): string {
  switch (status.status) {
    case 'loading':
      return 'load-graph'
    case 'ok':
      return 'checkmark'
    case 'warn':
      return 'alert_warn'
    case 'crit':
      return 'alert_crit'
  }
}
</script>

<template>
  <div class="status-box" :class="status.status">
    <CmkIcon :name="getIconName(status)" :title="status.tooltip" size="medium" variant="inline" />
    {{ status.tooltip }}
  </div>
</template>

<style scoped>
/* TODO: Can be removed when CMK-23811 is fixed */
.cmk-icon {
  display: inline-block;
}
.status-box {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  &.ok {
    background-color: rgb(from var(--success) r g b / 15%);
  }
  &.warn {
    background-color: rgb(from var(--color-warning) r g b / 15%);
  }
  &.crit {
    background-color: rgb(from var(--color-danger) r g b / 15%);
  }
}
</style>
