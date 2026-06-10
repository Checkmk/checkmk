<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { useTemplateRef } from 'vue'

import CmkIcon, { type CmkIconProps } from '@/components/CmkIcon'

defineProps<CmkIconProps>()

defineEmits(['click'])

const button = useTemplateRef<HTMLButtonElement>('button')

defineExpose({
  focus: () => {
    button.value?.focus()
  }
})
</script>

<template>
  <button
    ref="button"
    type="button"
    class="cmk-icon-button"
    :title="title"
    @click.prevent="
      (e) => {
        $emit('click', e)
      }
    "
  >
    <CmkIcon
      :name="name"
      :variant="variant"
      :size="size"
      :colored="colored"
      :rotate="rotate"
      :title="title"
    />
  </button>
</template>

<style scoped>
.cmk-icon-button {
  margin: 0;
  padding: 0;
  background: none;
  border: none;
  cursor: pointer;

  /* Collapse the inline-image baseline descender gap so the focus outline
     hugs the icon instead of leaving a strip below it. */
  display: inline-flex;
}

.cmk-icon-button:focus-visible {
  outline: revert;
}
</style>
