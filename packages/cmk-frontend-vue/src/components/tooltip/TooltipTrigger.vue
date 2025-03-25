<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { TooltipTrigger } from 'radix-vue'

defineEmits(['click'])

interface TooltipTriggerProps {
  asChild?: boolean
}

defineProps<TooltipTriggerProps>()
</script>

<template>
  <TooltipTrigger :as-child="!!asChild" @click="(event) => $emit('click', event)">
    <slot />
  </TooltipTrigger>
</template>
