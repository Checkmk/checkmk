/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * The breadcrumb levels above the SPA, handed in by the page that mounts it.
 *
 * They belong to the Checkmk main menu Maps hangs under, and naming that menu in
 * TypeScript would mirror a title the GUI already owns. The dashboard page hands
 * its own out the same way (``page_show_dashboard.py``'s ``initial_breadcrumb``).
 *
 * The map list puts its own level behind them; the views below it carry their
 * own breadcrumb, whose links load the view as a page.
 */
import type { BreadcrumbItem } from 'cmk-ui-library/components/CmkBreadcrumb'
import { type InjectionKey, inject, provide } from 'vue'

export const MAPS_BREADCRUMB_ROOT: InjectionKey<BreadcrumbItem[]> = Symbol('mapsBreadcrumbRoot')

export function provideMapsBreadcrumbRoot(root: BreadcrumbItem[]): void {
  provide(MAPS_BREADCRUMB_ROOT, root)
}

export function useMapsBreadcrumbRoot(): BreadcrumbItem[] {
  return inject(MAPS_BREADCRUMB_ROOT) ?? []
}
