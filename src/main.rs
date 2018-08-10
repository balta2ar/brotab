extern crate clap;
extern crate reqwest;

// use std::io;
use std::env;
use std::io::Read;
use std::net::{SocketAddr, TcpStream};
use std::thread;
use std::thread::JoinHandle;
use std::time::Duration;

use clap::{App, Arg, SubCommand};

static ASCII_LOWERCASE: &'static str = "abcdefghijklmnopqrstuvwxyz";

fn can_connect(port: u16) -> bool {
    let addr = SocketAddr::from(([127, 0, 0, 1], port));
    TcpStream::connect_timeout(&addr, Duration::from_millis(50)).is_ok()
}

fn get_available_ports() -> Vec<u16> {
    // Check first 10 ports starting from 4625
    (4625..).take(10).filter(|&x| can_connect(x)).collect()
}

fn list_tabs(port: u16) -> String {
    let url = format!("http://localhost:{}/list_tabs", port);
    let mut response = reqwest::get(url.as_str()).expect("Request failed");
    // println!("status: {}", response.status());

    // for header in response.headers().iter() {
    //     println!("header: {}: {}", header.name(), header.value_string());
    // }

    let mut buf = String::new();
    response
        .read_to_string(&mut buf)
        .expect("Cannot read response");

    buf
}

fn bt_list() {
    // println!("bt list");

    // for port in get_available_ports() {
    //     let buf = list_tabs(port);
    //     println!("response: {}", buf.len());
    // }

    let mut children: Vec<JoinHandle<_>> = vec![];
    for port in get_available_ports() {
        children.push(std::thread::spawn(move || -> String { list_tabs(port) }));
    }
    for (ch, child) in ASCII_LOWERCASE.chars().zip(children) {
        let unprefixed: String = child.join().unwrap();
        let prefixed = unprefixed
            .lines()
            .map(|x| format!("{}.{}", ch, x))
            .collect::<Vec<_>>()
            .join("\n");
        println!("{}", prefixed);
        // println!("response: {}", buf.len());
    }

    // println!("bt list done");
}

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
            SubCommand::with_name("clients")
            .about("List all available browser clients (mediators)")
        )
        .get_matches();

    match matches.subcommand() {
        ("list", Some(_m)) => bt_list(),
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
