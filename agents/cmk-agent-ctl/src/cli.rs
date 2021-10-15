use structopt::StructOpt;

#[derive(StructOpt)]
#[structopt(name = "cmk-agent-ctl", about = "Checkmk agent controller.")]
pub struct Args {
    #[structopt(help = "Execution mode, should be one of 'register', 'push', 'dump', 'status'")]
    pub mode: String,

    #[structopt(long, parse(from_str))]
    pub server: Option<Vec<String>>,
}
