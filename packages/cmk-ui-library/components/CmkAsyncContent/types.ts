/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Component } from 'vue'

/**
 * A body component and the promise that fills it.
 *
 * The consuming page owns both, so whatever container the body is dropped into
 * never imports feature-specific code.
 */
export interface CmkAsyncContentProps {
  /** The component rendered once the data is in, receiving it as `data`. */
  component: Component
  /**
   * Awaited on mount; the resolved value is passed as `data`. Left out where the
   * body has nothing to wait for.
   */
  load?: (() => Promise<unknown>) | undefined
  /**
   * Shown while `load` is pending. Falls back to a generic loading indicator
   * when not provided.
   */
  skeleton?: Component | undefined
  /** Static props forwarded verbatim to `component`. */
  props?: Record<string, unknown> | undefined
}
