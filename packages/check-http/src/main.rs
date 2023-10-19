use clap::Parser;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = check_http::cli::Cli::parse();
    Ok(check_http::check_http(args).await?)
}
