<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import NetworkFlowAutonomousSystemSlideIn from './AutonomousSystemSlideIn/NetworkFlowAutonomousSystemSlideIn.vue'
import NetworkFlowHostSlideIn from './HostSlideIn/NetworkFlowHostSlideIn.vue'
import type { NetworkFlowSlideIns } from './useNetworkFlowSlideIns'

/** Renders both network flow detail panels for a `useNetworkFlowSlideIns()` state. */
const props = defineProps<{ slideIns: NetworkFlowSlideIns }>()
</script>

<template>
  <NetworkFlowHostSlideIn
    :open="props.slideIns.hostOpen.value"
    :ip="props.slideIns.hostIp.value"
    @close="props.slideIns.closeHost()"
  />
  <NetworkFlowAutonomousSystemSlideIn
    :open="props.slideIns.autonomousSystemOpen.value"
    :asn="props.slideIns.autonomousSystemAsn.value"
    @close="props.slideIns.closeAutonomousSystem()"
  />
</template>
