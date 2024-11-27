<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from '@/components/CmkIcon.vue'
import QuickSetupAsync from './QuickSetupAsync.vue'
import type { QuickSetupAppProps } from './types'
import { onUnmounted, onBeforeMount } from 'vue'

defineProps<QuickSetupAppProps>()

let originalConsoleInfo: typeof console.info | undefined

onBeforeMount(() => {
  originalConsoleInfo = console.info
  console.info = () => {}
})

onUnmounted(() => {
  if (originalConsoleInfo) {
    console.info = originalConsoleInfo
  }
})
</script>
<template>
  <Suspense>
    <QuickSetupAsync
      :quick_setup_id="quick_setup_id"
      :toggle-enabled="toggleEnabled"
      :mode="mode"
      :object-id="objectId"
    />
    <template #fallback>
      <CmkIcon name="load-graph" size="xxlarge" />
    </template>
  </Suspense>
</template>

<style>
@import './variables.css';
</style>
