<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkTruncateText from 'cmk-ui-library/components/CmkTruncateText.vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'
</script>

<template>
  <!-- In a narrow cell, the start gets an ellipsis and the last 9 characters stay visible. -->
  <div style="width: 160px">
    <CmkTruncateText
      :text="untranslated('This is a long text that exceeds the width of its container')"
      :suffix-count="9"
    />
  </div>
</template>
