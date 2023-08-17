use clap::{Parser, Subcommand};
use std::fs::OpenOptions;
use std::io::Write;
use std::{thread, time};

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
    WithLogInC,
}

fn main() {
    let cli = Cli::parse();
    match cli.mode {
        Mode::Test => println!("test"),
        Mode::Daemon => loop {
            thread::sleep(time::Duration::from_millis(1000));
        },
        Mode::WithLogInC => loop {
            let mut f = OpenOptions::new()
                .write(true)
                .create(true)
                .append(true)
                .open("c:\\robot_mk_ext.log")
                .unwrap();
            thread::sleep(time::Duration::from_millis(1000));
            let data = "This is just for test\n";
            f.write_all(data.as_bytes()).expect("Unable to write data");
        },
    }
}
