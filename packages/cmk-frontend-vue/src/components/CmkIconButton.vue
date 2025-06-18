<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from '@/components/CmkIcon.vue'
import { type CmkIconProps } from '@/components/CmkIcon.vue'

defineProps<CmkIconProps>()

defineEmits(['click'])
</script>

<template>
  <button
    class="cmk-icon-button"
    @click.prevent="
      (e) => {
        $emit('click', e)
      }
    "
  >
    <CmkIcon :name="name" :variant="variant" :size="size" :rotate="rotate" :title="title" />
  </button>
</template>

<style scoped>
.cmk-icon-button {
  margin: 0;
  padding: 0;
  background: none;
  border: none;
  cursor: pointer;
}
</style>
