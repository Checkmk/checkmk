<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import LoadingIcon from '@/components/LoadingIcon.vue'
import QuickSetupAsync from './QuickSetupAsync.vue'
import type { QuickSetupAppProps } from './types'

defineProps<QuickSetupAppProps>()
</script>
<template>
  <Suspense>
    <QuickSetupAsync
      :quick_setup_id="quick_setup_id"
      :toggle-enabled="toggleEnabled"
      :mode="mode"
    />
    <template #fallback>
      <LoadingIcon />
    </template>
  </Suspense>
</template>

<style>
@import '@/assets/variables.css';
@import './variables.css';
</style>
