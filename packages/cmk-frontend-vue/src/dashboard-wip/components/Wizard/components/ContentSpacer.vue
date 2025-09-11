<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

interface ContentSpacerProps {
  variant?: 'blank' | 'line'
  height?: number
}

const props = withDefaults(defineProps<ContentSpacerProps>(), {
  variant: 'blank',
  height: 20
})

const pixelHeight = computed(() => `${props.height}px`)
</script>

<template>
  <div class="content-spacer">
    <hr v-if="variant === 'line'" class="content-spacer__horizontal-line" />
  </div>
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.content-spacer {
  flex: 1;
  display: flex;
  align-items: center;
  min-height: v-bind(pixelHeight);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.content-spacer__horizontal-line {
  width: 100%;
  border-color: var(--ux-theme-2);
}
</style>
