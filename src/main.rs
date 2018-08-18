extern crate clap;
extern crate reqwest;
extern crate tempfile;

mod net;

// use std::io;
use std::env;
use std::io::Read;
use std::thread;
use std::thread::JoinHandle;
use std::process::Command;
use std::fs::File;
use std::io::Write;

use clap::{App, Arg, SubCommand};

use net::get_available_ports;

static ASCII_LOWERCASE: &'static str = "abcdefghijklmnopqrstuvwxyz";


/// Create clients for all available ports
fn create_clients() -> Vec<BrowserClient> {
    get_available_ports().iter().map(|x| BrowserClient::new(*x)).collect()
}

struct BrowserClient {
    port: u16
}

impl BrowserClient {
    fn new(port: u16) -> BrowserClient {
        BrowserClient{ port: port }
    }

    fn list_tabs(&self) -> String {
        let url = format!("http://localhost:{}/list_tabs", self.port);
        let mut response = reqwest::get(url.as_str()).expect("Request failed");

        let mut buf = String::new();
        response
            .read_to_string(&mut buf)
            .expect("Cannot read response");

        buf
    }
}

fn get_editor_command() -> String {
    env::var("EDITOR").unwrap_or("nvim".to_string())
}

fn edit_text_in_editor(text: &String) -> Option<String> {
    // let mut tmpfile: File = tempfile::tempfile().unwrap();

    let mut tmpfile = tempfile::NamedTempFile::new().unwrap();
    write!(tmpfile, "{}", "before");
    let path = tmpfile.path().to_str().unwrap();
    println!("{}", path);

    let output = Command::new(get_editor_command()).arg(path).status().expect("Could not run
                                                                              nvim");
    if output.success() {
        let mut file = File::open(path).unwrap();
        let mut contents = String::new();
        file.read_to_string(&mut contents);
        return Some(contents);

        //return Some(String::from_utf8_lossy(&output.stdout).to_string())

        // return Some("".to_string())
    } else {
        println!("Editor quit with non zero exit code");
        return None
    }
}

fn bt_move() {
    let clients = create_clients();
    let before_tabs = clients[0].list_tabs();
    // println!("TABS: {}", before_tabs);
    if let Some(after_tabs) = edit_text_in_editor(&before_tabs) {
        println!("AFTER: {}", after_tabs);
    }
}

/// Ask all mediators to provide a list of their tabs and print them
fn bt_list() {
    let mut children: Vec<JoinHandle<_>> = vec![];
    for port in get_available_ports() {
        children.push(std::thread::spawn(move || -> String {
            let client = BrowserClient::new(port);
            client.list_tabs()
        }));
    }
    for (ch, child) in ASCII_LOWERCASE.chars().zip(children) {
        let unprefixed: String = child.join().unwrap();
        let prefixed = unprefixed
            .lines()
            .map(|x| format!("{}.{}", ch, x))
            .collect::<Vec<_>>()
            .join("\n");
        println!("{}", prefixed);
    }
}

/// List all available mediators (browser clients)
fn bt_clients() {
    // let checked_ports: Vec<_> = (0..10)
    //     .map(|x| x + 4625)
    //     .collect();
    // let mut children = vec![];
    // for port in checked_ports {
    //     children.push(thread::spawn(move || -> u16 {
    //         if can_connect(port) { port } else { 0 }
    //     }));
    // }
    // let available_ports = children.map()
    //
    // let ascii_lowercase = "abcdefghijklmnopqrstuvwxyz";
    // ascii_lowercase
    //     .chars()
    //     .zip(available_ports)
    //     .for_each(|(ch, port)| println!("{}.\tlocalhost:{}", ch, port));

    // let available_ports: Vec<_> = (0..10)
    //     .map(|x| x + 4625)
    //     .filter(|&x| can_connect(x))
    //     .collect();
    let available_ports = get_available_ports();
    // let ascii_lowercase = "abcdefghijklmnopqrstuvwxyz";
    ASCII_LOWERCASE
        .chars()
        .zip(available_ports)
        .for_each(|(ch, port)| println!("{}.\tlocalhost:{}", ch, port));
}

fn main() {
    let matches = App::new("BroTab Browser Tab management")
        .version("0.1.0")
        .author("Yuri Bochkarev <baltazar.bz@gmail.com>")
        .about("Helps you win at browser tab management")
        .subcommand(
            SubCommand::with_name("list")
            .about("List all available tabs")
        )
        .subcommand(
            SubCommand::with_name("move")
            .about("Move tabs around using your favorite editor")
        )
        .subcommand(
            SubCommand::with_name("clients")
            .about("List all available browser clients (mediators)")
        )
        .get_matches();

    match matches.subcommand() {
        ("list", Some(_m)) => bt_list(),
        ("move", Some(_m)) => bt_move(),
        ("clients", Some(_m)) => bt_clients(),
        _ => println!("No command or unknown specified. Get help using --help."),
    }

    // let args: Vec<String> = env::args().collect();
    // match args.len() {
    //     2 => {
    //         let command = &args[1];
    //         // println!("Your arguments: {:?}", command);
    //         match &command[..] {
    //             "list" => bt_list(),
    //             "clients" => bt_clients(),
    //             _ => {
    //                 eprintln!("Invalid command: {:?}", command);
    //             }
    //         }
    //     }
    //     _ => {
    //         println!("Not enough arguments: bt <command>");
    //         return;
    //     }
    // }
}
