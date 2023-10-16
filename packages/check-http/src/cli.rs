use crate::pwstore;
use anyhow::{anyhow, Result as AnyhowResult};
use clap::{Args, Parser};
use http::{HeaderName, HeaderValue, Method};

#[derive(Parser, Debug)]
#[command(about = "check_http")]
pub struct Cli {
    /// Username for HTTP Basic Auth
    #[arg(long, group = "authuser")]
    pub auth_user: Option<String>,

    #[command(flatten)]
    pub auth_pw: AuthPw,

    /// Additional header in the form NAME:VALUE. Use multiple times for additional headers.
    #[arg(short = 'k', long="header", value_parser=split_header)]
    pub headers: Option<Vec<(HeaderName, HeaderValue)>>,

    /// URL to check
    #[arg(short, long)]
    pub url: String,

    /// Set timeout in seconds
    #[arg(long, default_value_t = 10)]
    pub timeout: u64,

    /// Wait for document body
    #[arg(long, default_value_t = false)]
    pub without_body: bool,

    /// Set user-agent
    #[arg(long)]
    pub user_agent: Option<HeaderValue>,

    /// Set HTTP method. Default: GET
    #[arg(short='j', long, default_value_t=Method::GET)]
    pub method: Method,
}

#[derive(Args, Debug)]
#[group(multiple = false)]
pub struct AuthPw {
    /// Plain password for HTTP Basic Auth
    #[arg(long, requires = "authuser")]
    pub auth_pw_plain: Option<String>,

    /// Password for HTTP Basic Auth, provided as ID for password store lookup
    #[arg(long, requires = "authuser", value_parser=pwstore::password_from_store)]
    pub auth_pwstore: Option<String>,
}

fn split_header(header: &str) -> AnyhowResult<(HeaderName, HeaderValue)> {
    let Some((name, value)) = header.split_once(':') else {
        return Err(anyhow!("Invalid HTTP header: {} (missing ':')", header));
    };
    Ok((name.trim().parse()?, value.trim().parse()?))
}

#[test]
fn verify_cli() {
    use clap::CommandFactory;
    Cli::command().debug_assert()
}
