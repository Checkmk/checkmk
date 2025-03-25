<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkButton from '@/components/CmkButton.vue'
import CmkIcon from '@/components/CmkIcon.vue'
import CmkButtonSubmit from '@/components/CmkButtonSubmit.vue'
import CmkButtonCancel from '@/components/CmkButtonCancel.vue'

defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  <dl>
    <dt><code>&lt;CmkButton variant="primary"&gt;button&lt;/CmkButton&gt;</code></dt>
    <dd>
      <CmkButton variant="primary">button</CmkButton>
    </dd>

    <dt><code>&lt;CmkButton variant="secondary"&gt;button&lt;/CmkButton&gt;</code></dt>
    <dd>
      <CmkButton variant="secondary">button</CmkButton>
    </dd>

    <dt><code>&lt;CmkButton&gt;button&lt;/CmkButton&gt;</code></dt>
    <dd>
      <CmkButton>button</CmkButton>
    </dd>

    <dt><code>&lt;CmkButton variant="success"&gt;button&lt;/CmkButton&gt;</code></dt>
    <dd>
      <CmkButton variant="success">button</CmkButton>
    </dd>

    <dt><code>&lt;CmkButton variant="warning"&gt;button&lt;/CmkButton&gt;</code></dt>
    <dd>
      <CmkButton variant="warning">button</CmkButton>
    </dd>

    <dt><code>&lt;CmkButton variant="danger"&gt;button&lt;/CmkButton&gt;</code></dt>
    <dd>
      <CmkButton variant="danger">button</CmkButton>
    </dd>

    <dt><code>&lt;CmkButton variant="info"&gt;info&lt;/CmkButton&gt;</code></dt>
    <dd>
      <CmkButton variant="info">info</CmkButton>
    </dd>

    <dt><code>&lt;CmkButtonSubmit&gt;button&lt;/CmkButtonSubmit&gt;</code></dt>
    <dd>
      <CmkButtonSubmit>button</CmkButtonSubmit>
    </dd>

    <dt><code>&lt;CmkButtonCancel&gt;button&lt;/CmkButtonCancel&gt;</code></dt>
    <dd>
      <CmkButtonCancel>button</CmkButtonCancel>
    </dd>

    <dt>
      <code
        >&lt;CmkButton&gt;&lt;CmkIcon name="about_checkmk" variant="inline"
        /&gt;button&lt;/CmkButton&gt;</code
      >
    </dt>
    <dd>
      <CmkButton><CmkIcon name="about_checkmk" variant="inline" />button</CmkButton>
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
