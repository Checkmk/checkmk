<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import NotificationRules from '@/notification/components/NotificationRules.vue'
import type { RuleSection } from '@/notification/type_defs'

defineProps<{
  parameters: RuleSection[]
}>()
</script>

<template>
  <NotificationRules :rule_sections="parameters"></NotificationRules>
</template>

<style scoped></style>
