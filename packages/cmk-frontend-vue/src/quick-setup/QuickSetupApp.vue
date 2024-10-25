<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from '@/components/CmkIcon.vue'
import QuickSetupAsync from './QuickSetupAsync.vue'
import type { QuickSetupAppProps } from './types'
import { onBeforeMount, onUnmounted, getCurrentInstance } from 'vue'
import type { AppConfig, ComponentInternalInstance } from 'vue'

defineProps<QuickSetupAppProps>()

onBeforeMount(() => {
  const instance = getCurrentInstance() as ComponentInternalInstance | null

  if (instance && instance.appContext.config) {
    const originalWarnHandler: AppConfig['warnHandler'] = instance.appContext.config.warnHandler

    // Suppress warning about <Suspense> being an experimental feature explicitly here (since we use it intentionally)
    instance.appContext.config.warnHandler = (msg, instance, trace) => {
      if (msg.includes('<Suspense> is an experimental feature')) {
        return
      }
      if (originalWarnHandler) {
        originalWarnHandler(msg, instance, trace)
      }
    }

    onUnmounted(() => {
      if (originalWarnHandler !== undefined) {
        instance.appContext.config.warnHandler = originalWarnHandler
      }
    })
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
@import '@/assets/variables.css';
@import './variables.css';
</style>
