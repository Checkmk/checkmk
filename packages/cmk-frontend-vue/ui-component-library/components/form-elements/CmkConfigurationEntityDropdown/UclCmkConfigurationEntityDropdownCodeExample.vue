<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import CmkConfigurationEntityDropdown from '@/components/user-input/CmkConfigurationEntityDropdown'

const selectedId = ref<string | null>(null)
</script>

<template>
  <CmkConfigurationEntityDropdown
    v-model="selectedId"
    config-entity-type="notification_parameter"
    config-entity-type-specifier="slack"
    label="Notification parameter"
    :allow-editing-existing-elements="true"
  />
</template>
