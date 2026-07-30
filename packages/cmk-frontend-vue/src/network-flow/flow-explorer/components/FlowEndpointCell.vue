<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkChip from 'cmk-ui-library/components/CmkChip.vue'
import { computed } from 'vue'

import BaseCell from '@/monitoring/shared/components/cell/BaseCell.vue'

const props = defineProps<{
  columnId: string
  address: string
  port: number
  /** Autonomous system of the address; 0 means unresolved and is not shown. */
  asn: number
}>()

// Port 0 is what the flow carries for protocols without ports (ICMP), not a real
// port, so it is left off rather than rendered as ":0".
const endpoint = computed(() =>
  props.port === 0 ? props.address : `${props.address}:${props.port}`
)
const asnLabel = computed(() => (props.asn === 0 ? null : `AS${props.asn}`))
</script>

<template>
  <BaseCell class="network-flow-flow-endpoint-cell" :column-id="columnId" no-wrap>
    <span class="network-flow-flow-endpoint-cell__endpoint" :title="endpoint">{{ endpoint }}</span>
    <!-- as-div: a badge, not something to click. -->
    <CmkChip
      v-if="asnLabel"
      class="network-flow-flow-endpoint-cell__asn"
      size="small"
      variant="outline"
      color="info"
      as-div
    >
      {{ asnLabel }}
    </CmkChip>
  </BaseCell>
</template>

<style scoped>
.network-flow-flow-endpoint-cell__endpoint {
  overflow: hidden;
  text-overflow: ellipsis;
}

.network-flow-flow-endpoint-cell__asn {
  margin-left: var(--dimension-3);
  flex: 0 0 auto;
}
</style>
