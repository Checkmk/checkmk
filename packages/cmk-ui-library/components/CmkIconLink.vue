<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAutoIcon, { type AutoIconProps } from 'cmk-ui-library/components/CmkIcon/CmkAutoIcon.vue'
import { computed, useTemplateRef } from 'vue'

interface IconLinkNavProps {
  href: string
  target?: string | undefined
}

const props = defineProps<AutoIconProps & IconLinkNavProps>()

defineEmits(['click'])

const link = useTemplateRef<HTMLAnchorElement>('link')

// href/target aren't icon props: CmkAutoIcon renders a fragment (no single root to fall
// attrs through to), so passing them along via v-bind would trigger a Vue attrs warning.
//
// title is dropped too: the anchor below already carries it, and CmkIcon renders title as
// both the img's title and alt. Passing it through as well would give the img an alt text
// duplicating the anchor's own accessible name.
const iconProps = computed<AutoIconProps>(() => {
  const { href: _href, target: _target, title: _title, ...icon } = props
  return icon
})

defineExpose({
  focus: () => {
    link.value?.focus()
  }
})
</script>

<template>
  <a
    ref="link"
    class="cmk-icon-link"
    :href="href"
    :target="target"
    :title="title"
    @click="
      (e) => {
        $emit('click', e)
      }
    "
  >
    <CmkAutoIcon v-bind="iconProps" />
  </a>
</template>

<style scoped>
.cmk-icon-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: var(--dimension-2);
  border-radius: var(--dimension-2);
  color: inherit;
  text-decoration: none;
}

.cmk-icon-link:hover {
  background-color: var(--cmk-icon-link-hover-bg-color);
}

.cmk-icon-link:focus-visible {
  outline: revert;
}

body[data-theme='facelift'] .cmk-icon-link {
  --cmk-icon-link-hover-bg-color: var(--color-conference-grey-10);
}

body[data-theme='modern-dark'] .cmk-icon-link {
  --cmk-icon-link-hover-bg-color: var(--color-white-10);
}
</style>
