<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import { useInjectDrillDownSource } from '@/dashboard/composables/useDrillDownSource'
import { contextualLinkEntries } from '@/dashboard/lib/contextualLinkUrl'
import type { LinkProperties, ResolvedLink, VisualContext } from '@/dashboard/types/widget'

import ContextualLinkAnchor from './ContextualLinkAnchor.vue'

const props = defineProps<{
  links: ResolvedLink[]
  linkProperties: LinkProperties
  filters: VisualContext
  /** Opens the menu of several below this element instead of below the link. */
  reference?: HTMLElement | null | undefined
}>()

const open = defineModel<boolean>('open', { default: false })

defineSlots<{ default(props: { several: boolean }): unknown }>()

const drillDownSource = useInjectDrillDownSource()

const entries = computed(() =>
  contextualLinkEntries(props.links, props.linkProperties, props.filters, drillDownSource.value)
)
</script>

<template>
  <ContextualLinkAnchor
    v-slot="{ several }"
    v-model:open="open"
    :entries="entries"
    :reference="reference"
  >
    <slot :several="several" />
  </ContextualLinkAnchor>
</template>
