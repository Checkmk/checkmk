<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIndent from '@/components/CmkIndent.vue'
</script>

<template>
  <p>Top Level Content</p>
  <CmkIndent>
    <p>First Level Indentation</p>
    <CmkIndent error>
      <p>Second Level Indentation</p>
    </CmkIndent>
  </CmkIndent>
</template>
