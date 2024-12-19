<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { ref, type Ref } from 'vue'
import CmkIcon from '@/components/CmkIcon.vue'
import { type CmkIconVariants } from '@/components/CmkIcon.vue'

defineProps<{ screenshotMode: boolean }>()

const sizes: CmkIconVariants['size'][] = ['xsmall', 'small', 'medium', 'large', 'xlarge', 'xxlarge']
const variants: CmkIconVariants['variant'][] = ['plain', 'inline']
const title = 'Some title that is shown in a tooltip on hovering the icon'
const iconName = ref('continue')
const sizeRef: Ref<CmkIconVariants['size']> = ref('large')
const rotate = ref(90)
</script>

<template>
  <ul>
    <li v-for="variant in variants" :key="variant || 'dflt'">
      <b>variant "{{ variant }}"</b>
      <ul>
        <li v-for="size in sizes" :key="size || 'dflt'" class="demo-icon-element__entry">
          size "{{ size }}":
          <CmkIcon name="main_help" :variant="variant" :size="size" :title="title" />
        </li>
      </ul>
    </li>
  </ul>
  <div>
    <b>Dynamic CmkIcon by properties</b>
    <div>e.g. "main_help" or "main-help" or "main_help.svg"</div>
    <div>icon name: <input v-model="iconName" /></div>
    <div>size: <input v-model="sizeRef" /> ({{ sizes }})</div>
    <div>rotate (in degrees): <input v-model="rotate" /></div>
    <div>icon: <CmkIcon :name="iconName" :size="sizeRef" :rotate="rotate" /></div>
  </div>
</template>

<style scoped>
ul {
  list-style-type: none;
  margin-bottom: 40px;
  padding: 0;
}

li {
  margin: 1em;

  &.demo-icon-element__entry {
    display: flex;
  }
}

input {
  margin: 5px 10px;
}
</style>
