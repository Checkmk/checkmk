use clap::{Parser, Subcommand};
use std::io::Read;

#[derive(Parser)]
#[command(about = "RobotMk Windows agent extension.", version = "0.1")]
pub struct Cli {
    #[command(subcommand)]
    pub mode: Mode,
}
#[derive(Subcommand)]
pub enum Mode {
    Daemon,
    Test,
}

fn main() {
    let cli = Cli::parse();
    match cli.mode {
        Mode::Test => println!("test"),
        Mode::Daemon => {
            println!("Press ENTER to stop daemon...");
            let buffer = &mut [0u8];
            std::io::stdin().read_exact(buffer).unwrap()
        }
    }
}
