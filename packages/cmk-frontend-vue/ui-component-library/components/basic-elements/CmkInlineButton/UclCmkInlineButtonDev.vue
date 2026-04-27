<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkInlineButton from '@/components/user-input/CmkInlineButton.vue'

defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  <dl>
    <dt><code>&lt;CmkInlineButton&gt;Add item&lt;/CmkInlineButton&gt;</code></dt>
    <dd>
      <CmkInlineButton>Add item</CmkInlineButton>
    </dd>

    <dt><code>&lt;CmkInlineButton /&gt;</code></dt>
    <dd>
      <CmkInlineButton />
    </dd>

    <dt><code>&lt;CmkInlineButton icon="delete"&gt;Remove&lt;/CmkInlineButton&gt;</code></dt>
    <dd>
      <CmkInlineButton icon="delete">Remove</CmkInlineButton>
    </dd>

    <dt>
      <code>&lt;CmkInlineButton :disabled="true"&gt;Add item&lt;/CmkInlineButton&gt;</code>
    </dt>
    <dd>
      <CmkInlineButton :disabled="true">Add item</CmkInlineButton>
    </dd>
  </dl>
</template>

<style scoped>
dt {
  margin-top: 2em;
  margin-bottom: 0.5em;
}

dd {
  margin: 0;
  padding: 0;
}
</style>
