<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import { splitOnQuery } from '../lib/search'

const props = defineProps<{ text: string; query: string }>()

const parts = computed(() => splitOnQuery(props.text, props.query))
</script>

<template>
  <template v-if="parts === null">{{ text }}</template>
  <template v-else
    >{{ parts.before }}<mark>{{ parts.match }}</mark
    >{{ parts.after }}</template
  >
</template>

<style scoped>
mark {
  background: transparent;
  color: var(--default-select-focus-color);
  font-weight: inherit;
}
</style>
