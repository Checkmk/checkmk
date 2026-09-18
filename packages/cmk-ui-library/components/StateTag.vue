<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

export type StateTone = 'ok' | 'warning' | 'critical' | 'unknown' | 'pending'

/**
 * `compact` narrows the tag for a state column too tight for a spelled-out
 * label; `inline` also shrinks it to sit inside a line of text.
 */
export type StateTagSize = 'default' | 'compact' | 'inline'

/** Fixes the tag width, which differs by how long the longest label of each is. */
export type StateTagKind = 'host' | 'service'

withDefaults(
  defineProps<{
    label: TranslatedString
    tone: StateTone
    kind: StateTagKind
    size?: StateTagSize
    /** Renders the state as no longer backed by a fresh check result. */
    stale?: boolean | undefined
  }>(),
  { size: 'default' }
)
</script>

<template>
  <span
    class="cmk-state-tag"
    :class="[
      `cmk-state-tag--${tone}`,
      `cmk-state-tag--${kind}`,
      `cmk-state-tag--size-${size}`,
      { 'cmk-state-tag--stale': stale }
    ]"
    >{{ label }}</span
  >
</template>

<style scoped>
.cmk-state-tag {
  --state-tag-height: var(--dimension-7);

  display: inline-flex;
  box-sizing: border-box;
  height: var(--state-tag-height);
  width: var(--state-tag-width);
  align-items: center;
  justify-content: center;
  overflow: hidden;
  margin: 0;
  padding: 0 var(--dimension-4);
  border-radius: calc(var(--state-tag-height) / 2);
  background: var(--state-tag-background);
  color: var(--state-tag-font-color);
  font-size: 10px;
  font-weight: var(--font-weight-bold);
  line-height: normal;
  white-space: nowrap;
}

.cmk-state-tag--size-default.cmk-state-tag--host {
  --state-tag-width: 75px;
}

.cmk-state-tag--size-default.cmk-state-tag--service {
  --state-tag-width: 81px;
}

.cmk-state-tag--size-compact {
  --state-tag-width: 34px;

  padding: 0 var(--dimension-3);
}

/*
 * Sized by its own text rather than by the line it sits in: a cell sets a line
 * height for the row, and a flex badge inheriting that grows well past the small
 * tag it is supposed to be.
 */
.cmk-state-tag--size-inline {
  --state-tag-height: var(--dimension-5);
  --state-tag-width: 34px;

  padding: 0 var(--dimension-3);
  font-size: 9px;
}

.cmk-state-tag--stale {
  opacity: 0.7;
  background:
    repeating-linear-gradient(-25deg, transparent 0 3px, rgb(0 0 0 / 25%) 4px 7px, transparent 8px),
    var(--state-tag-background);
}

/* Pinned to the palette rather than to theme variables: a state reads the same in both themes. */
.cmk-state-tag--ok {
  --state-tag-background: var(--color-corporate-green-80);
  --state-tag-font-color: var(--color-corporate-green-10);
}

.cmk-state-tag--warning {
  --state-tag-background: var(--color-yellow-60);
  --state-tag-font-color: var(--color-yellow-100);
}

.cmk-state-tag--critical {
  --state-tag-background: var(--color-dark-red-60);
  --state-tag-font-color: var(--color-dark-red-0);
}

.cmk-state-tag--unknown {
  --state-tag-background: var(--color-orange-70);
  --state-tag-font-color: var(--white);
}

.cmk-state-tag--pending {
  --state-tag-background: var(--color-mist-grey-80);
  --state-tag-font-color: var(--color-mist-grey-0);
}
</style>
