<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  title: string
  mnemonic: string | null
}>()

const index = computed(() =>
  props.mnemonic ? props.title.toLowerCase().indexOf(props.mnemonic.toLowerCase()) : -1
)
</script>

<template>
  <span v-if="index < 0">{{ title }}</span>
  <span v-else
    >{{ title.slice(0, index) }}<span class="mm-mnemonic-title__key">{{ title.charAt(index) }}</span
    >{{ title.slice(index + 1) }}</span
  >
</template>

<style scoped>
.mm-mnemonic-title__key {
  text-decoration: underline;
  text-decoration-thickness: 2px;
  text-underline-offset: 2px;
}
</style>
