<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { CollapsibleRoot, useForwardPropsEmits } from 'radix-vue'
import type { CollapsibleRootEmits, CollapsibleRootProps } from 'radix-vue'

const props = defineProps<CollapsibleRootProps>()
const emits = defineEmits<CollapsibleRootEmits>()

const forwarded = useForwardPropsEmits(props, emits)
</script>

<template>
  <!-- @vue-expect-error Radix-vue props doesn't follow our exactOptionalPropertyTypes rule -->
  <CollapsibleRoot v-slot="{ open: openSlot }" v-bind="forwarded" class="ui-collapsible">
    <slot :open="openSlot" />
  </CollapsibleRoot>
</template>

<style scoped>
.ui-collapsible {
  padding-top: 2px;
}
</style>
