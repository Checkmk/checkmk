<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type IFrameContent } from '@/dashboard-wip/types/widget.ts'

import DashboardContentContainer from './DashboardContentContainer.vue'
import type { ContentProps } from './types.ts'

const props = defineProps<ContentProps>()
const content = props.content as IFrameContent
</script>

<template>
  <DashboardContentContainer v-bind="generalSettings">
    <div class="db-content-iframe__div">
      <iframe class="db-content-iframe__iframe" allowtransparency="true" :src="content.url" />
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
