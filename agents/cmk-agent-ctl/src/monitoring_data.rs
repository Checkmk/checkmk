use std::io::{Read, Result};
use std::os::unix::net::UnixStream;

pub fn collect() -> Result<Vec<u8>> {
    let mut mondata: Vec<u8> = vec![];
    UnixStream::connect("/run/check-mk-agent.socket")?.read_to_end(&mut mondata)?;
    return Ok(mondata);
}
