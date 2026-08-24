/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

/** a view's rows are server-rendered, so refreshing one means asking cmk-frontend to
 * re-fetch its content container. Drop this once views render through Vue.
 */
declare const cmk: {
  utils: {
    reload_content_now: (onContentReady?: () => void) => void
  }
}

/** Re-fetch the surrounding page's content in place. The global time picker and this refresh
 * state live outside that container, so both survive which is what lets a refresh keep the
 * range the user is looking at instead of dropping back to the page's initial one.
 *
 * `onContentReady` fires while the outgoing content is still mounted, immediately before it is
 * replaced, and on every path the fetch can take - including its failure.
 */
export function reloadPageContent(onContentReady?: () => void): void {
  cmk.utils.reload_content_now(onContentReady)
}
