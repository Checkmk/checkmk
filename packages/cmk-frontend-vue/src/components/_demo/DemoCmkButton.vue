<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkButton from '@/components/CmkButton.vue'
</script>

<template>
  <dl>
    <dt><code>&lt;CmkButton type="primary"&gt;button&lt;/CmkButton&gt;</code></dt>
    <dd>
      <CmkButton type="primary">button</CmkButton>
    </dd>
    <dt><code>&lt;CmkButton&gt;button&lt;/CmkButton&gt;</code></dt>
    <dd>
      <CmkButton>button</CmkButton>
    </dd>
    <dt><code>&lt;CmkButton type="tertiary"&gt;button&lt;/CmkButton&gt;</code></dt>
    <dd>
      <CmkButton type="tertiary">button</CmkButton>
    </dd>
    <dt><code>&lt;CmkButton variant="cancel"&gt;button&lt;/CmkButton&gt;</code></dt>
    <dd>
      <CmkButton variant="cancel">button</CmkButton>
    </dd>
    <dt><code>&lt;CmkButton variant="submit"&gt;button&lt;/CmkButton&gt;</code></dt>
    <dd>
      <CmkButton variant="submit">button</CmkButton>
    </dd>
    <dt>TODO: add CmkButton with Icon, after icon component is ready</dt>
    <dd></dd>
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
