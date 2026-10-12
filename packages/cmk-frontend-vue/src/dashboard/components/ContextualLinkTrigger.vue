<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import { firstContextualLinkUrl } from '@/dashboard/lib/contextualLinkUrl'
import type { LinkProperties, ResolvedLink, VisualContext } from '@/dashboard/types/widget'

const props = defineProps<{
  links: ResolvedLink[]
  linkProperties: LinkProperties
  filters: VisualContext
}>()

const href = computed(() =>
  firstContextualLinkUrl(props.links, props.linkProperties, props.filters)
)
</script>

<template>
  <a v-if="href !== null" :href="href"><slot /></a>
  <slot v-else />
</template>
