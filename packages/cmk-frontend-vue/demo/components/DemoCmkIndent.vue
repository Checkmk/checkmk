<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIndent from '@/components/CmkIndent.vue'

defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  <p>Topic:</p>
  <CmkIndent>
    <p>related topic</p>
    <CmkIndent>
      <p>even more info</p>
    </CmkIndent>
  </CmkIndent>
</template>
