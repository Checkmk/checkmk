// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Shared resolution infrastructure used by multiple validators. Each module
//! turns a static `Package` view into an answer about runtime semantics:
//! "where does this symlink chain lead?", etc.

pub(crate) mod symlinks;
