<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { CollapsibleContent, type CollapsibleContentProps } from 'radix-vue'

const props = defineProps<CollapsibleContentProps>()
</script>

<template>
  <!-- @vue-expect-error Radix-vue props doesn't follow our exactOptionalPropertyTypes rule -->
  <CollapsibleContent v-bind="props" class="ui-collapsible-content">
    <slot />
  </CollapsibleContent>
</template>

<style scoped lang="scss">
.ui-collapsible-content {
  &[data-state='open'] {
    animation: slideDown 300ms ease-out;
  }

  &[data-state='closed'] {
    animation: slideUp 300ms ease-out;
  }
}

@mixin zero-height {
  overflow: hidden;
  height: 0;
}

@mixin full-height {
  overflow: hidden;
  height: var(--radix-collapsible-content-height);
}

@keyframes slideDown {
  from {
    @include zero-height;
  }
  to {
    @include full-height;
  }
}

@keyframes slideUp {
  from {
    @include full-height;
  }
  to {
    @include zero-height;
  }
}
</style>
