<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import sanitizeHtml from 'sanitize-html'

defineProps<{ html: string | undefined }>()

const options: sanitizeHtml.IOptions = {
  // Following cmk/utils/escaping.py
  allowedTags: [
    'h1',
    'h2',
    'b',
    'tt',
    'i',
    'u',
    'hr',
    'br',
    'nobr',
    'pre',
    'sup',
    'p',
    'li',
    'ul',
    'ol',
    'a'
  ],
  allowedSchemes: ['http', 'https', 'mailto']
}
</script>

<template>
  <!-- eslint-disable-next-line vue/no-v-html -->
  <span v-if="html" v-html="sanitizeHtml(html, options)"></span>
</template>
