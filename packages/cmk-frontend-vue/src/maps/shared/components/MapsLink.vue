<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import type { NavTarget } from '@/maps/services/NavigationService'
import { useNavigation } from '@/maps/services/context'

const props = defineProps<{ to: NavTarget }>()

const nav = useNavigation()
const href = computed(() => nav.href(props.to))

function onClick(event: MouseEvent): void {
  // Let the browser handle modified clicks (new tab/window) and non-primary
  // buttons via the real href; only intercept a plain left click for SPA nav.
  if (
    event.defaultPrevented ||
    event.button !== 0 ||
    event.metaKey ||
    event.ctrlKey ||
    event.shiftKey ||
    event.altKey
  ) {
    return
  }
  event.preventDefault()
  nav.navigate(props.to)
}
</script>

<template>
  <a :href="href" @click="onClick"><slot /></a>
</template>
