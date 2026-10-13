<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
What a static map looks like, for the list: hosts, services and groups placed on
a canvas, each showing its state. An illustration with sample names — the map's
own objects are drawn once it is opened.
-->
<script setup lang="ts">
import { untranslated } from 'cmk-ui-library/lib/i18n'
import type { CSSProperties } from 'vue'

import type { ThumbnailState } from '@/maps/home/components/thumbnails/palette'

type NodeState = ThumbnailState | 'unknown' | 'neutral'

interface Node {
  x: number
  y: number
  r: number
  state: NodeState
  /** The object-type initial the icon carries (H)ost, (S)ervice, host(G)roup … */
  initial: string
  fontSize: number
  /** Two-letter initials need to be pulled together to fit the icon. */
  tight?: boolean
  /** Only the objects whose name the illustration spells out carry a caption. */
  caption?: string
  captionWidth?: number
}

const GRID_COLUMNS: readonly number[] = [64, 128, 192]
const GRID_ROWS: readonly number[] = [43, 86]

const NODES: readonly Node[] = [
  {
    x: 36,
    y: 30,
    r: 13,
    state: 'ok',
    initial: 'H',
    fontSize: 8,
    caption: 'web-srv-01',
    captionWidth: 36
  },
  {
    x: 212,
    y: 24,
    r: 11,
    state: 'crit',
    initial: 'S',
    fontSize: 8,
    caption: 'HTTP Check',
    captionWidth: 38
  },
  {
    x: 118,
    y: 58,
    r: 14,
    state: 'ok',
    initial: 'HG',
    fontSize: 6.5,
    tight: true,
    caption: 'linux-servers',
    captionWidth: 40
  },
  {
    x: 58,
    y: 100,
    r: 11,
    state: 'warn',
    initial: 'S',
    fontSize: 8,
    caption: 'Disk Usage',
    captionWidth: 40
  },
  {
    x: 190,
    y: 82,
    r: 11,
    state: 'ok',
    initial: 'S',
    fontSize: 8,
    caption: 'CPU Load',
    captionWidth: 40
  },
  { x: 152, y: 20, r: 9, state: 'neutral', initial: 'M', fontSize: 7 },
  { x: 234, y: 108, r: 10, state: 'ok', initial: 'SG', fontSize: 6.5, tight: true },
  { x: 96, y: 112, r: 9, state: 'unknown', initial: 'H', fontSize: 7 }
]

function captionY(node: Node): number {
  return node.y + node.r + 5
}

/**
 * Checkmk's theme carries a ``* { font-size: inherit; letter-spacing: … }``
 * (``_main.scss``), and an SVG presentation attribute loses to any rule that
 * matches the element — so a ``font-size="8"`` on the text would render at the
 * page's font size instead. The per-node sizes therefore have to be style
 * declarations; the ones that are the same for every node live in the CSS
 * below.
 */
function initialStyle(node: Node): CSSProperties {
  return {
    fontSize: `${node.fontSize}px`,
    letterSpacing: node.tight ? '-0.5px' : '0'
  }
}

/**
 * Only the two states an operator scans for glow. A filter primitive takes its
 * colour from its own ``flood-color``, not from the shape it is applied to, so
 * there is one filter per glowing state rather than one parameterised filter.
 * The ids repeat across the cards on a page, which is harmless: every card
 * defines the identical filter.
 */
function glowFilter(state: NodeState): string | undefined {
  return state === 'ok' || state === 'crit'
    ? `url(#maps-static-map-thumbnail-glow-${state})`
    : undefined
}
</script>

<template>
  <svg viewBox="0 0 256 128" class="maps-static-map-thumbnail">
    <defs>
      <filter id="maps-static-map-thumbnail-glow-ok" x="-30%" y="-30%" width="160%" height="160%">
        <feDropShadow
          dx="0"
          dy="0"
          stdDeviation="2.5"
          class="maps-static-map-thumbnail__glow--ok"
        />
      </filter>
      <filter id="maps-static-map-thumbnail-glow-crit" x="-30%" y="-30%" width="160%" height="160%">
        <feDropShadow
          dx="0"
          dy="0"
          stdDeviation="2.5"
          class="maps-static-map-thumbnail__glow--crit"
        />
      </filter>
    </defs>
    <rect width="256" height="128" class="maps-static-map-thumbnail__canvas" />
    <line
      v-for="x in GRID_COLUMNS"
      :key="`c${x}`"
      :x1="x"
      y1="0"
      :x2="x"
      y2="128"
      class="maps-static-map-thumbnail__grid"
    />
    <line
      v-for="y in GRID_ROWS"
      :key="`r${y}`"
      x1="0"
      :y1="y"
      x2="256"
      :y2="y"
      class="maps-static-map-thumbnail__grid"
    />
    <g
      v-for="(node, index) in NODES"
      :key="index"
      class="maps-static-map-thumbnail__node"
      :class="`maps-static-map-thumbnail__node--${node.state}`"
    >
      <circle
        :cx="node.x"
        :cy="node.y"
        :r="node.r"
        class="maps-static-map-thumbnail__icon"
        :filter="glowFilter(node.state)"
      />
      <text
        :x="node.x"
        :y="node.y"
        :style="initialStyle(node)"
        text-anchor="middle"
        dominant-baseline="central"
        class="maps-static-map-thumbnail__initial"
      >
        {{ untranslated(node.initial) }}
      </text>
      <template v-if="node.caption && node.captionWidth">
        <rect
          :x="node.x - node.captionWidth / 2"
          :y="captionY(node)"
          :width="node.captionWidth"
          height="7"
          rx="2"
          class="maps-static-map-thumbnail__caption-bg"
        />
        <text
          :x="node.x"
          :y="captionY(node) + 4"
          text-anchor="middle"
          dominant-baseline="central"
          class="maps-static-map-thumbnail__caption"
        >
          {{ untranslated(node.caption) }}
        </text>
      </template>
    </g>
  </svg>
</template>

<style scoped>
.maps-static-map-thumbnail__canvas {
  fill: var(--maps-map-thumbnail-canvas);
}

.maps-static-map-thumbnail__grid {
  stroke: var(--maps-map-thumbnail-grid);
  stroke-width: 0.5;
}

.maps-static-map-thumbnail__node--ok {
  --maps-static-map-thumbnail-state: var(--maps-map-thumbnail-ok);
}

.maps-static-map-thumbnail__node--warn {
  --maps-static-map-thumbnail-state: var(--maps-map-thumbnail-warn);

  /* Yellow carries dark text, the other states light. */
  --maps-static-map-thumbnail-on-state: var(--maps-map-thumbnail-on-warn);
}

.maps-static-map-thumbnail__node--crit {
  --maps-static-map-thumbnail-state: var(--maps-map-thumbnail-crit);
}

.maps-static-map-thumbnail__node--unknown {
  --maps-static-map-thumbnail-state: var(--maps-map-thumbnail-unknown);
}

.maps-static-map-thumbnail__node--neutral {
  --maps-static-map-thumbnail-state: var(--maps-map-thumbnail-neutral);
}

.maps-static-map-thumbnail__icon {
  fill: var(--maps-static-map-thumbnail-state);
}

.maps-static-map-thumbnail__glow--ok {
  flood-color: color-mix(in srgb, var(--maps-map-thumbnail-ok) 45%, transparent);
}

.maps-static-map-thumbnail__glow--crit {
  flood-color: color-mix(in srgb, var(--maps-map-thumbnail-crit) 50%, transparent);
}

.maps-static-map-thumbnail__initial {
  fill: var(--maps-static-map-thumbnail-on-state, var(--maps-map-thumbnail-on-state));
  font-weight: var(--font-weight-bold);
}

.maps-static-map-thumbnail__caption-bg {
  fill: color-mix(in srgb, var(--maps-map-thumbnail-canvas) 65%, transparent);
}

/* The size and the spacing have to be declared, not set as attributes: see
   ``initialStyle``. */
.maps-static-map-thumbnail__caption {
  fill: color-mix(in srgb, var(--maps-map-thumbnail-label) 70%, transparent);
  font-size: 5px;
  letter-spacing: 0;
}
</style>
