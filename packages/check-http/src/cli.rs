use crate::pwstore;
use anyhow::{anyhow, Result as AnyhowResult};
use clap::{Args, Parser, ValueEnum};
use http::{HeaderName, HeaderValue, Method};
use std::time::Duration;

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
    #[arg(short, long, default_value = "10", value_parser=parse_seconds)]
    pub timeout: Duration,

    /// Wait for document body
    #[arg(long, default_value_t = false)]
    pub without_body: bool,

    /// Set user-agent
    #[arg(long)]
    pub user_agent: Option<HeaderValue>,

    /// Set HTTP method. Default: GET
    #[arg(short='j', long, default_value_t=Method::GET)]
    pub method: Method,

    /// How to handle redirected pages. sticky is like follow but stick to the
    /// specified IP address. stickyport also ensures port stays the same.
    #[arg(short = 'f', long, default_value = "follow")]
    pub onredirect: OnRedirect,

    /// Maximal number of redirects
    #[arg(long, default_value_t = 15)]
    pub max_redirs: usize,
}

#[derive(Clone, Debug, ValueEnum)]
pub enum OnRedirect {
    Ok,
    Warning,
    Critical,
    Follow,
    Sticky,
    Stickyport,
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

fn parse_seconds(secs: &str) -> AnyhowResult<Duration> {
    Ok(Duration::from_secs(secs.parse()?))
}

#[cfg(test)]
mod tests {
    use super::*;
    use clap::CommandFactory;
    use http::{HeaderName, HeaderValue};
    use std::str::FromStr;

    #[test]
    fn verify_cli() {
        Cli::command().debug_assert()
    }

    #[test]
    fn test_split_header() {
        assert!(split_header(":value").is_err());
        assert!(split_header("name value").is_err());
        assert!(split_header("name:some\r\nvalue").is_err());
        assert_eq!(
            split_header("name:value").unwrap(),
            (
                HeaderName::from_str("name").unwrap(),
                HeaderValue::from_str("value").unwrap()
            )
        );
        assert_eq!(
            split_header("name:").unwrap(),
            (
                HeaderName::from_str("name").unwrap(),
                HeaderValue::from_str("").unwrap()
            )
        );
        assert_eq!(
            split_header("name  :  value  ").unwrap(),
            (
                HeaderName::from_str("name").unwrap(),
                HeaderValue::from_str("value").unwrap()
            )
        );
    }
}
