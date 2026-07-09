<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { VisuallyHidden } from 'reka-ui'
import { computed } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'

interface CmkVisuallyHiddenProps {
  /** Text exposed to assistive technologies but hidden from sighted users. */
  text: TranslatedString
  /** DOM id, so the node can be referenced via `aria-describedby`/`aria-labelledby`. */
  id?: string
  /**
   * How assistive tech surfaces the text:
   * - `'off'` (default): a static label, changes are not auto-announced.
   * - `'polite'`: a live region (`role="status"`) whose changes are announced at the next pause.
   * - `'assertive'`: a live region (`role="alert"`) whose changes interrupt immediately.
   */
  live?: 'off' | 'polite' | 'assertive'
}

const props = withDefaults(defineProps<CmkVisuallyHiddenProps>(), { live: 'off' })

// `role` is derived from `live` rather than taken as its own prop so the two can never disagree:
// ARIA defines `role="status"` as an implicit polite live region and `role="alert"` as an assertive
// one, so pairing each `live` value with its matching role is what makes the announcement land
// reliably across screen readers. `live: 'off'` is silent and therefore carries no announcing role.
const role = computed<'status' | 'alert' | undefined>(() =>
  props.live === 'assertive' ? 'alert' : props.live === 'polite' ? 'status' : undefined
)
</script>

<template>
  <VisuallyHidden :id="id" feature="fully-hidden" :role="role" :aria-live="live">{{
    text
  }}</VisuallyHidden>
</template>
