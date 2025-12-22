<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIconButton from '@/components/CmkIconButton.vue'

interface CloseButtonEmits {
  close: []
}

defineEmits<CloseButtonEmits>()
</script>

<template>
  <div class="db-close-button">
    <CmkIconButton name="close" size="xsmall" @click="$emit('close')" />
  </div>
</template>

<style scoped>
.db-close-button {
  position: absolute;
  top: 5px;
  right: 10px;
}
</style>
