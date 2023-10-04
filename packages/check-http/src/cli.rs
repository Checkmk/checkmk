
use clap::Parser;

#[derive(Parser, Debug)]
#[command(about = "check_http")]
pub struct Args {
    /// URL to check
    #[arg(short, long)]
    pub url: String,

    /// Set timeout in seconds
    #[arg(long, default_value_t = 10)]
    pub timeout: u64,

    /// Wait for document body
    #[arg(long)]
    pub without_body: bool,

    /// Set user-agent
    #[arg(long)]
    pub user_agent: Option<String>,
}