<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
interface IconButtonProps {
  /** @property {string} label - Button's caption */
  label: string

  /** @property {string} ariaLabel - Aria label for the button */
  ariaLabel?: string
}

const props = defineProps<IconButtonProps>()
defineEmits(['click'])
</script>

<template>
  <button class="button" :aria-label="ariaLabel || label" @click="$emit('click')">
    <span>{{ props.label }}</span>
  </button>
</template>

<style scoped></style>
