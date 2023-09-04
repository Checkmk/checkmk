use std::env::Args;

const PW_STORE_ARG: &str = "--pwstore=";

pub fn patch_args(args: Args) -> Vec<String> {
    let mut args_vec: Vec<_> = args.collect();

    let first_arg = &args_vec[1];
    if !first_arg.starts_with(PW_STORE_ARG) {
        return args_vec;
    };

    let parts: Vec<_> = first_arg[PW_STORE_ARG.len()..].splitn(3, '@').collect();

    if parts.len() != 3 {
        println!("pwstore: Invalid --pwstore entry: {}", first_arg);
        std::process::exit(3);
    }

    let num_arg: usize = parts[0].parse().unwrap();
    let pos_arg: usize = parts[1].parse().unwrap();
    let pw_id = parts[2];

    let pw_arg = &args_vec[num_arg];
    args_vec[num_arg] = format!(
        "{}{}{}",
        &pw_arg[..pos_arg],
        pw_id,
        &pw_arg[pos_arg + pw_id.len()..]
    );

    args_vec.remove(1);
    args_vec
}
