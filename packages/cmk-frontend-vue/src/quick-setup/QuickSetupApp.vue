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
import { useErrorBoundary } from '@/components/useErrorBoundary'

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
// eslint-disable-next-line @typescript-eslint/naming-convention
const { ErrorBoundary } = useErrorBoundary()
</script>
<template>
  <ErrorBoundary>
    <!-- this seems okay, but it does not show a good error message !-->
    <Suspense>
      <QuickSetupAsync
        :quick_setup_id="quick_setup_id"
        :toggle_enabled="toggle_enabled"
        :mode="mode"
        :object_id="object_id"
      />
      <template #fallback>
        <CmkIcon name="load-graph" size="xxlarge" />
      </template>
    </Suspense>
  </ErrorBoundary>
</template>

<style>
@import './variables.css';
</style>
