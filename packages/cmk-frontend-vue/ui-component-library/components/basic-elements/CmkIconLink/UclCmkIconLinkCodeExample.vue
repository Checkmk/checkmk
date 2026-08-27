<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIconLink from 'cmk-ui-library/components/CmkIconLink.vue'
</script>

<template>
  <CmkIconLink name="main-help" size="medium" title="Get Help" href="https://docs.checkmk.com" />
  <CmkIconLink
    name="more-actions"
    primary-color="font"
    size="medium"
    title="More actions"
    href="https://docs.checkmk.com"
    target="_blank"
  />
</template>
