<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkCode from '@/components/CmkCode.vue'

const mySnippet = `const greet = () => {
  console.log("Hello Checkmk!");
};
greet();`
</script>

<template>
  <CmkCode title="Greeting Function" :code_txt="mySnippet" />
</template>
