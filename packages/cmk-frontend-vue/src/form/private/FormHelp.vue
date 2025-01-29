<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkHtml from '@/components/CmkHtml.vue'

defineProps<{
  help: string
}>()
</script>

<template>
  <div v-if="help" class="help vue_help">
    <div class="info_icon">
      <img class="icon" />
    </div>
    <div class="help_text"><CmkHtml :html="help" /></div>
  </div>
</template>
