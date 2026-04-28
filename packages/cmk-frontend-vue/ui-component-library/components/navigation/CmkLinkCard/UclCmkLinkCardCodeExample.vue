<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkLinkCard from '@/components/CmkLinkCard'
</script>

<template>
  <CmkLinkCard
    title="Checkmk Documentation"
    subtitle="Learn how to configure and use Checkmk."
    icon-name="about-checkmk"
    url="https://docs.checkmk.com"
    variant="standard"
    :open-in-new-tab="true"
  />
</template>
