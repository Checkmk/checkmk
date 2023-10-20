use clap::{Parser, Subcommand};
#[macro_use]
extern crate windows_service;
use windows_service::service_dispatcher;

use lazy_static::lazy_static;
use std::ffi::OsString;
use std::sync::Mutex;
use std::time::Duration;
use windows_service::service::{
    ServiceControl, ServiceControlAccept, ServiceExitCode, ServiceState, ServiceStatus, ServiceType,
};
use windows_service::service_control_handler::{
    self, ServiceControlHandlerResult, ServiceStatusHandle,
};

const SERVICE_NAME: &str = "agent_keeper";
const SERVICE_DISPLAY_NAME: &str = "Agent keeper";
const SERVICE_DESCRIPTION: &str = "Checkmk agent keeper service";
const VERSION: &str = "2.3.0";

lazy_static! {
    static ref SERVICE_STATUS_HANDLE: Mutex<Option<ServiceStatusHandle>> = Mutex::new(None);
    static ref EXE_DIR: Mutex<String> = Mutex::new(".".to_string());
    static ref WORK_DIR: Mutex<String> = Mutex::new(".".to_string());
}

pub fn get_exe_dir() -> String {
    EXE_DIR.lock().unwrap().to_string()
}

pub fn get_work_dir() -> String {
    WORK_DIR.lock().unwrap().to_string()
}

define_windows_service!(ffi_service_main, service_main);

#[derive(Parser, Debug)]
#[command(name = "")]
#[command(about = "Checkmk agent keeper service", version = VERSION)]
struct Cli {
    /// Use once (-v) for logging level INFO and twice (-vv) for logging level DEBUG.
    #[arg(short, long, action = clap::ArgAction::Count)]
    verbose: u8,

    #[command(subcommand)]
    mode: Option<Mode>,

    #[arg(short, long, action = clap::ArgAction::Set)]
    exe_dir: Option<String>,

    #[arg(short, long, action = clap::ArgAction::Set)]
    work_dir: Option<String>,
}

#[derive(Subcommand, Debug)]
pub enum Mode {
    Install,
    Uninstall,
    DryRun,
}

fn install_service(
    service_name: &str,
    service_display_name: &str,
    service_description: &str,
) -> windows_service::Result<()> {
    use windows_service::{
        service::{ServiceAccess, ServiceErrorControl, ServiceInfo, ServiceStartType},
        service_manager::{ServiceManager, ServiceManagerAccess},
    };

    let manager_access = ServiceManagerAccess::CONNECT | ServiceManagerAccess::CREATE_SERVICE;
    let service_manager = ServiceManager::local_computer(None::<&str>, manager_access)?;

    let service_binary_path = ::std::env::current_exe().unwrap();

    let service_info = ServiceInfo {
        name: OsString::from(service_name),
        display_name: OsString::from(service_display_name),
        service_type: ServiceType::OWN_PROCESS,
        start_type: ServiceStartType::OnDemand,
        error_control: ServiceErrorControl::Normal,
        executable_path: service_binary_path,
        launch_arguments: vec!["--exe-dir", &get_exe_dir(), "--work-dir", &get_work_dir()]
            .into_iter()
            .map(OsString::from)
            .collect(),
        dependencies: vec![],
        account_name: None, // run as System
        account_password: None,
    };
    let service = service_manager.create_service(&service_info, ServiceAccess::CHANGE_CONFIG)?;
    service.set_description(service_description)?;
    Ok(())
}

fn uninstall_service(service_name: &str) -> windows_service::Result<()> {
    use std::{thread::sleep, time::Instant};

    use windows_service::{
        service::ServiceAccess,
        service_manager::{ServiceManager, ServiceManagerAccess},
    };
    use windows_sys::Win32::Foundation::ERROR_SERVICE_DOES_NOT_EXIST;

    let manager_access = ServiceManagerAccess::CONNECT;
    let service_manager = ServiceManager::local_computer(None::<&str>, manager_access)?;

    let service_access = ServiceAccess::QUERY_STATUS | ServiceAccess::STOP | ServiceAccess::DELETE;
    let service = service_manager.open_service(service_name, service_access)?;

    // The service will be marked for deletion as long as this function call succeeds.
    // However, it will not be deleted from the database until it is stopped and all open handles to it are closed.
    service.delete()?;
    // Our handle to it is not closed yet. So we can still query it.
    if service.query_status()?.current_state != ServiceState::Stopped {
        // If the service cannot be stopped, it will be deleted when the system restarts.
        service.stop()?;
    }
    // Explicitly close our open handle to the service. This is automatically called when `service` goes out of scope.
    drop(service);

    // Win32 API does not give us a way to wait for service deletion.
    // To check if the service is deleted from the database, we have to poll it ourselves.
    let start = Instant::now();
    let timeout = Duration::from_secs(5);
    while start.elapsed() < timeout {
        if let Err(windows_service::Error::Winapi(e)) =
            service_manager.open_service(SERVICE_NAME, ServiceAccess::QUERY_STATUS)
        {
            if e.raw_os_error() == Some(ERROR_SERVICE_DOES_NOT_EXIST as i32) {
                println!("{SERVICE_NAME} is deleted.");
                return Ok(());
            }
        }
        sleep(Duration::from_secs(1));
    }
    println!("{SERVICE_NAME} is marked for deletion.");

    Ok(())
}

fn service_main(arguments: Vec<OsString>) {
    if let Err(_e) = run_service(arguments) {
        // Handle error in some way.
    }
}

const RUNNING_STATUS: ServiceStatus = ServiceStatus {
    service_type: ServiceType::OWN_PROCESS,
    current_state: ServiceState::Running,
    controls_accepted: ServiceControlAccept::STOP,
    exit_code: ServiceExitCode::Win32(0),
    checkpoint: 0,
    wait_hint: Duration::from_secs(10),
    process_id: None,
};

const STOPPED_STATUS: ServiceStatus = ServiceStatus {
    service_type: ServiceType::OWN_PROCESS,
    current_state: ServiceState::Stopped,
    controls_accepted: ServiceControlAccept::SHUTDOWN,
    exit_code: ServiceExitCode::Win32(0),
    checkpoint: 0,
    wait_hint: Duration::from_secs(10),
    process_id: None,
};

fn run_service(_arguments: Vec<OsString>) -> windows_service::Result<()> {
    _register_service()?;
    _set_service_status(RUNNING_STATUS)
}

fn _register_service() -> windows_service::Result<()> {
    let event_handler = move |control_event| -> ServiceControlHandlerResult {
        match control_event {
            ServiceControl::Stop => {
                if let Err(e) = _set_service_status(STOPPED_STATUS) {
                    println!("Log {e:?}");
                    ServiceControlHandlerResult::Other(2)
                } else {
                    ServiceControlHandlerResult::NoError
                }
            }
            ServiceControl::Interrogate => ServiceControlHandlerResult::NoError,
            _ => ServiceControlHandlerResult::NoError,
        }
    };
    let status_handle = service_control_handler::register(SERVICE_NAME, event_handler)?;
    let mut handle = SERVICE_STATUS_HANDLE.lock().unwrap();
    if handle.is_none() {
        *handle = Some(status_handle);
    }
    Ok(())
}

fn _set_service_status(status: ServiceStatus) -> windows_service::Result<()> {
    if let Some(handle) = *SERVICE_STATUS_HANDLE.lock().unwrap() {
        handle.set_service_status(status)
    } else {
        // TODO(sk): log
        Ok(())
    }
}

fn main() -> Result<(), windows_service::Error> {
    let r = Cli::parse();
    *EXE_DIR.lock().unwrap() = r.exe_dir.unwrap_or_else(get_default_exe_dir);
    *WORK_DIR.lock().unwrap() = r.work_dir.unwrap_or_else(get_default_work_dir);
    match r.mode {
        None => service_dispatcher::start(SERVICE_NAME, ffi_service_main)?,
        Some(Mode::Install) => {
            install_service(SERVICE_NAME, SERVICE_DISPLAY_NAME, SERVICE_DESCRIPTION)?
        }
        Some(Mode::Uninstall) => uninstall_service(SERVICE_NAME)?,
        Some(Mode::DryRun) => println!(
            "Dry Run Mode, exe dir: '{}' work dir: '{}'",
            get_exe_dir(),
            get_work_dir()
        ),
    }

    Ok(())
}

fn get_default_exe_dir() -> String {
    let exe_path = std::env::current_exe().expect("You have no access rights for exe");
    exe_path
        .parent()
        .expect("You have no access rights for exe dir")
        .to_string_lossy()
        .to_string()
}

fn get_default_work_dir() -> String {
    get_default_exe_dir()
}
