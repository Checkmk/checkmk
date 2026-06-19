<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { untranslated } from '@/lib/i18n'

import CmkVisuallyHidden from '@/components/CmkVisuallyHidden.vue'
</script>

<template>
  <!-- A static label only assistive tech reads. -->
  <CmkVisuallyHidden :text="untranslated('Required field')" />

  <!-- A polite live region: changes to the text are announced. -->
  <CmkVisuallyHidden :text="untranslated('June 2026')" live="polite" />
</template>
