<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type IFrameContent } from '@/dashboard/types/widget.ts'

import DashboardContentContainer from './DashboardContentContainer.vue'
import type { ContentProps } from './types.ts'

interface DashboardContentIFrameProps extends ContentProps<IFrameContent> {
  contentCenter?: boolean
}

const { contentCenter } = defineProps<DashboardContentIFrameProps>()
</script>

<template>
  <DashboardContentContainer
    :effective-title="effectiveTitle"
    :general_settings="general_settings"
    :content-center="contentCenter"
  >
    <div class="db-content-i-frame__div">
      <iframe class="db-content-i-frame__iframe" allowtransparency="true" :src="content.url" />
    </div>
  </DashboardContentContainer>
</template>

<style scoped>
.db-content-i-frame__div {
  height: 100%;
  overflow: hidden;
  -webkit-overflow-scrolling: touch;
}

.db-content-i-frame__iframe {
  height: 100%;
  width: 100%;
  border: none;
}
</style>
