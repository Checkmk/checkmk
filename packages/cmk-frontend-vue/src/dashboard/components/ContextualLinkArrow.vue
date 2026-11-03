<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!-- Marks a link that opens a menu of several. For HTML; SVG figures draw their own. -->
<script setup lang="ts">
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
</script>

<template>
  <CmkMultitoneIcon
    name="triangle-up"
    :rotate="180"
    primary-color="font"
    size="xxsmall"
    class="db-contextual-link-anchor__arrow"
  />
</template>
