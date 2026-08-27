<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAutoIcon, { type AutoIconProps } from 'cmk-ui-library/components/CmkIcon/CmkAutoIcon.vue'
import { computed, useTemplateRef } from 'vue'

const props = defineProps<AutoIconProps>()

defineEmits(['click'])

const button = useTemplateRef<HTMLButtonElement>('button')

// title is dropped: the button below already carries it, and CmkIcon renders title as both
// the img's title and alt. Passing it through as well would give the img an alt text
// duplicating the button's own accessible name.
const iconProps = computed<AutoIconProps>(() => {
  const { title: _title, ...icon } = props
  return icon
})

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
    <CmkAutoIcon v-bind="iconProps" />
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

/* Mirrors CmkButton, so a disabled icon button does not read as an enabled one. */
.cmk-icon-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
