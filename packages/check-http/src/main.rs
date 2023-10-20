use check_http::{check_http, cli::Cli};
use clap::Parser;

#[tokio::main]
async fn main() {
    let args = Cli::parse();
    let output = check_http(args).await;
    println!("{}", output);
    std::process::exit(output.state.into());
}
