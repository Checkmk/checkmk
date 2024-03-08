// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#[cfg(unix)]
pub mod linux;
#[cfg(unix)]
#[allow(unused_imports)]
pub use linux::{is_elevation_required, is_port_available};

#[cfg(windows)]
pub mod win;
#[cfg(windows)]
#[allow(unused_imports)]
pub use win::{is_elevation_required, is_port_available};
