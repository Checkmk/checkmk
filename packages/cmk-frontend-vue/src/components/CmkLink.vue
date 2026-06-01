<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

export interface CmkLinkProps {
  href: string
  target?: string | undefined
}

defineProps<CmkLinkProps>()

const anchorRef = ref<HTMLAnchorElement | null>(null)

defineExpose({
  focus: () => {
    anchorRef.value?.focus()
  }
})
</script>

<template>
  <a ref="anchorRef" :href="href" :target="target" class="cmk-link">
    <slot />
  </a>
</template>

<style scoped>
.cmk-link {
  display: flex;
  flex-direction: row;
  gap: var(--dimension-3, 4px);
  color: inherit;
  width: 100%;
  font-size: var(--font-size-normal, 12px);
  font-style: normal;
  font-weight: var(--font-weight-default, 400);
  line-height: normal;
  text-decoration-line: underline;
  text-decoration-style: solid;
  text-decoration-skip-ink: auto;
  text-decoration-thickness: auto;
  text-underline-offset: auto;
  text-underline-position: from-font;

  &:hover {
    color: var(--cmk-link-hover-color, #15d1a0);
  }

  &:focus-visible {
    outline: revert;
  }
}
</style>
