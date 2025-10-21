<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { TooltipProvider } from 'radix-vue'

interface TooltipProviderProps {
  delayDuration?: number
}

const props = withDefaults(defineProps<TooltipProviderProps>(), {
  delayDuration: 700
})
</script>

<template>
  <TooltipProvider :delay-duration="props.delayDuration">
    <slot />
  </TooltipProvider>
</template>
