<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkButton from '@/components/CmkButton.vue'
import CmkButtonSubmit from '@/components/CmkButtonSubmit.vue'
import CmkButtonCancel from '@/components/CmkButtonCancel.vue'
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
    <dt><code>&lt;CmkButton type="transparent"&gt;button&lt;/CmkButton&gt;</code></dt>
    <dd>
      <CmkButton type="transparent">button</CmkButton>
    </dd>
    <dt><code>&lt;CmkButtonCancel&gt;button&lt;/CmkButtonCancel&gt;</code></dt>
    <dd>
      <CmkButtonCancel>button</CmkButtonCancel>
    </dd>
    <dt><code>&lt;CmkButtonSubmit&gt;button&lt;/CmkButtonSubmit&gt;</code></dt>
    <dd>
      <CmkButtonSubmit>button</CmkButtonSubmit>
    </dd>
    <dt><code>&lt;CmkButton spacing="small"&gt;button&lt;/CmkButton&gt;</code></dt>
    <dd>
      <CmkButton spacing="small">button</CmkButton>
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
