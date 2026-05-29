//! WebSocket broadcaster — pushes state/say/slice messages to the desktop app.
//!
//! Protocol mirrors v0.1 Python server so the existing Tauri frontend works
//! against this Rust backend without changes.

use std::sync::Arc;

use futures_util::{SinkExt, StreamExt};
use parking_lot::Mutex;
use serde_json::Value;
use tokio::net::TcpListener;
use tokio::sync::broadcast;
use tokio_tungstenite::tungstenite::Message;

use crate::state::Chibi;
use crate::system_info::SystemReader;

pub const DEFAULT_HOST: &str = "127.0.0.1";
pub const DEFAULT_PORT: u16 = 9876;
const STATE_PUSH_INTERVAL_SECS: u64 = 2;

#[derive(Clone)]
pub struct Broadcaster {
    tx: broadcast::Sender<String>,
}

impl Broadcaster {
    pub fn new() -> Self {
        let (tx, _) = broadcast::channel(64);
        Self { tx }
    }

    pub fn send(&self, msg: &Value) {
        if let Ok(payload) = serde_json::to_string(msg) {
            // ignore "no subscribers" error
            let _ = self.tx.send(payload);
        }
    }

    pub fn subscribe(&self) -> broadcast::Receiver<String> {
        self.tx.subscribe()
    }

    pub fn subscriber_count(&self) -> usize {
        self.tx.receiver_count()
    }
}

pub async fn run_ws_server(
    host: &str,
    port: u16,
    state: Arc<Chibi>,
    broadcaster: Broadcaster,
) -> anyhow::Result<()> {
    let addr = format!("{host}:{port}");
    let listener = TcpListener::bind(&addr).await?;
    tracing::info!("ws server listening on ws://{addr}");

    let sysreader = Arc::new(Mutex::new(SystemReader::default()));
    {
        // periodic state push
        let state = Arc::clone(&state);
        let sysreader = Arc::clone(&sysreader);
        let broadcaster = broadcaster.clone();
        tokio::spawn(async move {
            let mut tick =
                tokio::time::interval(std::time::Duration::from_secs(STATE_PUSH_INTERVAL_SECS));
            loop {
                tick.tick().await;
                let snap = sysreader.lock().read();
                let mood = state.compute_mood(&snap);
                let payload = state.snapshot(&snap, mood);
                broadcaster.send(&serde_json::json!({
                    "type": "state",
                    "payload": payload,
                }));
            }
        });
    }

    loop {
        let (stream, peer) = match listener.accept().await {
            Ok(p) => p,
            Err(e) => {
                tracing::warn!("accept failed: {e}");
                continue;
            }
        };
        let state = Arc::clone(&state);
        let sysreader = Arc::clone(&sysreader);
        let broadcaster = broadcaster.clone();
        tokio::spawn(async move {
            if let Err(e) = handle_client(stream, peer, state, sysreader, broadcaster).await {
                tracing::debug!("ws client error: {e}");
            }
        });
    }
}

async fn handle_client(
    stream: tokio::net::TcpStream,
    peer: std::net::SocketAddr,
    state: Arc<Chibi>,
    sysreader: Arc<Mutex<SystemReader>>,
    broadcaster: Broadcaster,
) -> anyhow::Result<()> {
    let ws = tokio_tungstenite::accept_async(stream).await?;
    tracing::info!("ws client connected from {peer}");
    let (mut write, mut read) = ws.split();

    // Send initial state immediately
    {
        let snap = sysreader.lock().read();
        let mood = state.compute_mood(&snap);
        let payload = state.snapshot(&snap, mood);
        let msg = serde_json::json!({"type": "state", "payload": payload});
        write
            .send(Message::Text(serde_json::to_string(&msg)?))
            .await?;
    }

    let mut rx = broadcaster.subscribe();
    loop {
        tokio::select! {
            broadcast_msg = rx.recv() => {
                match broadcast_msg {
                    Ok(text) => {
                        if write.send(Message::Text(text)).await.is_err() {
                            break;
                        }
                    }
                    Err(broadcast::error::RecvError::Lagged(_)) => continue,
                    Err(_) => break,
                }
            }
            incoming = read.next() => {
                match incoming {
                    Some(Ok(Message::Close(_))) | None => break,
                    Some(Ok(_)) => { /* clients are read-only for v0.2 alpha */ }
                    Some(Err(_)) => break,
                }
            }
        }
    }
    tracing::info!("ws client disconnected from {peer}");
    Ok(())
}
