<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
import { type DashboardContentContainerProps } from './DashboardContentContainer.vue'

export interface DashboardContentIFrameProps {
  generalSettings: DashboardContentContainerProps
  iframeUrl: string
}
</script>

<script setup lang="ts">
import DashboardContentContainer from './DashboardContentContainer.vue'

const { generalSettings, iframeUrl } = defineProps<DashboardContentIFrameProps>()
</script>

<template>
  <DashboardContentContainer v-bind="generalSettings">
    <div class="db-content-iframe__div">
      <iframe class="db-content-iframe__iframe" allowtransparency="true" :src="iframeUrl" />
    </div>
  </DashboardContentContainer>
</template>

<style scoped>
.db-content-iframe__div {
  height: 100%;
  overflow: hidden;
  -webkit-overflow-scrolling: touch;
}

.db-content-iframe__iframe {
  height: 100%;
  width: 100%;
  border: none;
}
</style>
