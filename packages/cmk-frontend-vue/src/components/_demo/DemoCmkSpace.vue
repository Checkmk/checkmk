<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkSpace from '@/components/CmkSpace.vue'

defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  <dl>
    <dt><code>!&lt;CmkSpace /&gt;!</code></dt>
    <dd>!<CmkSpace />!</dd>
  </dl>
</template>
