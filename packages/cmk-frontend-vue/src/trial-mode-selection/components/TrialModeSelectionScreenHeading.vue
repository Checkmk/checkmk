<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import { type ComponentPublicInstance, onMounted, ref } from 'vue'

const heading = ref<ComponentPublicInstance | null>(null)

/**
 * Leaving a screen unmounts the control that was just activated, and the browser then
 * resets focus to the document body: a keyboard user loses their place and a screen
 * reader announces nothing. The arriving screen's heading takes the focus instead.
 *
 * Every screen heads its content with this, so no screen can forget. One with a better
 * entry point than its title - the code boxes - focuses that from its own mounted hook,
 * which runs after this one.
 */
onMounted(() => {
  const element = heading.value?.$el
  if (element instanceof HTMLElement) {
    element.focus()
  }
})
</script>

<template>
  <CmkHeading ref="heading" type="h1" tabindex="-1"><slot /></CmkHeading>
</template>
