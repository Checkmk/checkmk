<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import CmkSearchInput from '@/components/CmkSearchInput.vue'

const query = ref('')

function onSearch(value: string): void {
  console.log('search submitted:', value)
}
</script>

<template>
  <CmkSearchInput v-model="query" placeholder="Search hosts…" @search="onSearch" />
</template>
