<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { NetworkFlowFlowExplorerApp } from 'cmk-shared-typing/typescript/network_flow/flow_explorer'

defineProps<NetworkFlowFlowExplorerApp>()
</script>

<template>
  <div class="network-flow-flow-explorer-app" />
</template>

<style scoped>
.network-flow-flow-explorer-app {
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding-bottom: var(--spacing);
  padding-right: var(--spacing);
}
</style>
