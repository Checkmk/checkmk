<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { IconSizeNames } from '@/components/CmkIcon'
import CmkIconButton from '@/components/CmkIconButton.vue'

defineProps<{ screenshotMode: boolean }>()

const sizes: IconSizeNames[] = ['xsmall', 'small', 'medium', 'large', 'xlarge', 'xxlarge']
</script>

<template>
  <dl>
    <dt><code>&lt;CmkIconButton name="main-help" /&gt;</code></dt>
    <dd>
      <CmkIconButton name="main-help" />
    </dd>

    <dt><code>&lt;CmkIconButton name="main-help" title="Get Help" /&gt;</code></dt>
    <dd>
      <CmkIconButton name="main-help" title="Get Help" />
    </dd>

    <dt>Sizes</dt>
    <dd class="ucl-cmk-icon-button-dev__row">
      <div v-for="size in sizes" :key="size" class="ucl-cmk-icon-button-dev__size-entry">
        <span>{{ size }}</span>
        <CmkIconButton name="main-help" :size="size" :title="size" />
      </div>
    </dd>

    <dt>Various icons</dt>
    <dd class="ucl-cmk-icon-button-dev__row">
      <CmkIconButton name="close" title="Close" size="medium" />
      <CmkIconButton name="delete" title="Delete" size="medium" />
      <CmkIconButton name="edit" title="Edit" size="medium" />
      <CmkIconButton name="plus" title="Add" size="medium" />
    </dd>
  </dl>
</template>

<style scoped>
dt {
  margin-top: 2em;
  margin-bottom: 0.5em;
  font-weight: bold;
}

dd {
  margin: 0;
  padding: 0;
}

.ucl-cmk-icon-button-dev__row {
  display: flex;
  align-items: center;
  gap: 1em;
}

.ucl-cmk-icon-button-dev__size-entry {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25em;
}
</style>
