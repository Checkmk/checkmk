/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Breakpoint, Layout, LayoutItem } from 'grid-layout-plus'

export type ResponsiveGridInternalBreakpoint = Breakpoint

export type ResponsiveGridInternalArrangementElement = LayoutItem
export type ResponsiveGridInternalArrangement = Layout
export type ResponsiveGridInternalLayout = Partial<
  Record<ResponsiveGridInternalBreakpoint, ResponsiveGridInternalArrangement>
>

export interface ResponsiveGridConfiguredInternalLayouts {
  default: ResponsiveGridInternalLayout
  [name: string]: ResponsiveGridInternalLayout
}
