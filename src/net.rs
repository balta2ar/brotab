
use std::net::{SocketAddr, TcpStream};
use std::time::Duration;


/// Check whether specified port can be connected to
pub fn can_connect(port: u16) -> bool {
    let addr = SocketAddr::from(([127, 0, 0, 1], port));
    TcpStream::connect_timeout(&addr, Duration::from_millis(50)).is_ok()
}

/// Get a list of available ports starting from 4625
pub fn get_available_ports() -> Vec<u16> {
    // Check first 10 ports starting from 4625
    (4625..).take(10).filter(|&x| can_connect(x)).collect()
}
