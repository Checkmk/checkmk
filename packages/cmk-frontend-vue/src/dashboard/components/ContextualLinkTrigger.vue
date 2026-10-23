<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import { contextualLinkEntries } from '@/dashboard/lib/contextualLinkUrl'
import type { LinkProperties, ResolvedLink, VisualContext } from '@/dashboard/types/widget'

import ContextualLinkChooser from './ContextualLinkChooser.vue'

const props = defineProps<{
  links: ResolvedLink[]
  linkProperties: LinkProperties
  filters: VisualContext
}>()

const entries = computed(() =>
  contextualLinkEntries(props.links, props.linkProperties, props.filters)
)
</script>

<template>
  <a v-if="entries.length === 1" :href="entries[0]!.href"><slot /></a>
  <ContextualLinkChooser v-else-if="entries.length > 1" :entries="entries">
    <a role="button" tabindex="0" class="db-contextual-link-trigger__chooser"><slot /></a>
  </ContextualLinkChooser>
  <slot v-else />
</template>

<style scoped>
/* Without an href, nothing would show that the element opens the menu. */
.db-contextual-link-trigger__chooser {
  cursor: pointer;
}
</style>
