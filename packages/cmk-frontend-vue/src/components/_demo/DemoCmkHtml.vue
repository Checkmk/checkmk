<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkHtml from '@/components/CmkHtml.vue'

defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  <dl>
    <dt>Simple styling</dt>
    <dd>
      in: &lt;h1&gt;Heading&lt;/h1&gt;&lt;tt&gt;foo()&lt;/tt&gt; &lt;b&gt;bold&lt;/b&gt;
      &lt;i&gt;italics&lt;/i&gt;
      <br />
      out: <CmkHtml html="<h1>Heading</h1><tt>foo()</tt> <b>bold</b> <i>italics</i>" />
    </dd>
  </dl>
  <dl>
    <dt>A link</dt>
    <dd>
      in: &lt;a href='https://checkmk.com'&gt;Checkmk&lt;/a&gt;
      <br />
      out: <CmkHtml html="<a href='https://checkmk.com'>Checkmk</a>" />
    </dd>
  </dl>
  <dl>
    <dt>Some dangerous stuff</dt>
    <dd>
      in: &lt;script&gt;alert(1)&lt;/script&gt;"
      <br />
      out: <CmkHtml html="<script>alert(1)</script>" />
    </dd>
  </dl>
</template>
