//! chibi-mcp v0.2 — Rust MCP server with WebSocket broadcast.
//!
//! Drop-in replacement for the v0.1 Python server. Same WebSocket protocol on
//! ws://127.0.0.1:9876 so the existing Tauri frontend keeps working.

mod state;
mod system_info;
mod ws_server;

use std::sync::Arc;

use once_cell::sync::OnceCell;
use parking_lot::Mutex;
use rmcp::handler::server::wrapper::Parameters;
use rmcp::schemars::JsonSchema;
use rmcp::{
    handler::server::tool::ToolRouter,
    model::{CallToolResult, Content, ServerCapabilities, ServerInfo},
    tool, tool_handler, tool_router,
    transport::stdio,
    ErrorData as McpError, ServerHandler, ServiceExt,
};
use serde::Deserialize;
use serde_json::json;

use crate::state::Tteoki;
use crate::system_info::SystemReader;
use crate::ws_server::{Broadcaster, DEFAULT_HOST, DEFAULT_PORT};

static GLOBAL_STATE: OnceCell<Arc<Tteoki>> = OnceCell::new();
static GLOBAL_BROADCASTER: OnceCell<Broadcaster> = OnceCell::new();
static GLOBAL_SYSREADER: OnceCell<Arc<Mutex<SystemReader>>> = OnceCell::new();

const SAY_MAX_LEN: usize = 200;

#[derive(Deserialize, JsonSchema)]
pub struct SayArgs {
    /// Short message (≤200 chars; longer is truncated with "…").
    pub text: String,
}

#[derive(Deserialize, JsonSchema)]
pub struct SliceIntervalArgs {
    /// New slice interval (every N Claude tool calls). Default is 10.
    pub n: u32,
}

#[derive(Clone)]
pub struct ChibiMcp {
    tool_router: ToolRouter<Self>,
}

#[tool_router]
impl ChibiMcp {
    fn new() -> Self {
        Self {
            tool_router: Self::tool_router(),
        }
    }

    #[tool(
        description = "Return tteoki's current mood, system metrics, counters, and timing. Counts as a Claude interaction; every N calls fires a slice event."
    )]
    async fn get_pet_state(&self) -> Result<CallToolResult, McpError> {
        let state = GLOBAL_STATE.get().expect("state init");
        let sysreader = GLOBAL_SYSREADER.get().expect("sys init");
        let broadcaster = GLOBAL_BROADCASTER.get().expect("ws init");

        let result = state.record_call(false);
        if result.sliced {
            broadcaster.send(&json!({"type": "slice"}));
        }

        let snap = sysreader.lock().read();
        let mood = state.compute_mood(&snap);
        let mut payload = state.snapshot(&snap, mood);
        payload["last_call_result"] = json!({
            "call_count": result.call_count,
            "calls_since_slice": result.calls_since_slice,
            "slices_today": result.slices_today,
            "sliced": result.sliced,
        });

        let json_text = serde_json::to_string_pretty(&payload)
            .map_err(|e| McpError::internal_error(e.to_string(), None))?;
        Ok(CallToolResult::success(vec![Content::text(json_text)]))
    }

    #[tool(
        description = "Make tteoki say something via a speech bubble in the desktop app. Text is truncated to 200 chars and control characters are stripped."
    )]
    async fn pet_say(
        &self,
        Parameters(args): Parameters<SayArgs>,
    ) -> Result<CallToolResult, McpError> {
        let state = GLOBAL_STATE.get().expect("state init");
        let broadcaster = GLOBAL_BROADCASTER.get().expect("ws init");

        let safe = sanitize_say(&args.text);
        let result = state.record_call(false);
        if result.sliced {
            broadcaster.send(&json!({"type": "slice"}));
        }
        broadcaster.send(&json!({"type": "say", "text": safe}));

        Ok(CallToolResult::success(vec![Content::text(
            serde_json::to_string_pretty(&json!({
                "spoken": safe,
                "broadcasted": broadcaster.subscriber_count() > 0,
            }))
            .unwrap_or_default(),
        )]))
    }

    #[tool(
        description = "Manually trigger a slice (resets the lengthen cycle, fires a slice event)."
    )]
    async fn slice_now(&self) -> Result<CallToolResult, McpError> {
        let state = GLOBAL_STATE.get().expect("state init");
        let broadcaster = GLOBAL_BROADCASTER.get().expect("ws init");

        let result = state.record_call(true);
        broadcaster.send(&json!({"type": "slice"}));

        Ok(CallToolResult::success(vec![Content::text(
            serde_json::to_string_pretty(&json!({
                "forced": true,
                "slices_today": result.slices_today,
                "calls_total": result.call_count,
            }))
            .unwrap_or_default(),
        )]))
    }

    #[tool(
        description = "Change how often (every N Claude tool calls) tteoki gets sliced. Default 10. Suggested: 5, 10, 25, 50, 100."
    )]
    async fn set_slice_interval(
        &self,
        Parameters(args): Parameters<SliceIntervalArgs>,
    ) -> Result<CallToolResult, McpError> {
        let state = GLOBAL_STATE.get().expect("state init");
        let (prev, new) = state.set_slice_interval(args.n);
        Ok(CallToolResult::success(vec![Content::text(
            serde_json::to_string_pretty(&json!({"previous": prev, "current": new}))
                .unwrap_or_default(),
        )]))
    }
}

#[tool_handler]
impl ServerHandler for ChibiMcp {
    fn get_info(&self) -> ServerInfo {
        ServerInfo {
            instructions: Some(
                "tteoki — Korean rice cake desktop pet. v0.2 Rust server with WebSocket broadcast."
                    .into(),
            ),
            capabilities: ServerCapabilities::builder().enable_tools().build(),
            ..Default::default()
        }
    }
}

fn sanitize_say(text: &str) -> String {
    let mut cleaned: String = text
        .chars()
        .filter(|c| !c.is_control() || *c == '\t' || *c == '\n')
        .collect();
    cleaned = cleaned.replace(['\r', '\n'], " ").trim().to_string();
    if cleaned.chars().count() > SAY_MAX_LEN {
        cleaned = cleaned.chars().take(SAY_MAX_LEN - 1).collect();
        cleaned.push('…');
    }
    cleaned
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt()
        .with_writer(std::io::stderr)
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_env("CHIBI_LOG")
                .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("info")),
        )
        .init();

    // Global singletons
    let state = Arc::new(Tteoki::new());
    GLOBAL_STATE.set(Arc::clone(&state)).ok();
    GLOBAL_BROADCASTER.set(Broadcaster::new()).ok();
    GLOBAL_SYSREADER
        .set(Arc::new(Mutex::new(SystemReader::default())))
        .ok();

    let host = std::env::var("CHIBI_WS_HOST").unwrap_or_else(|_| DEFAULT_HOST.to_string());
    let port: u16 = std::env::var("CHIBI_WS_PORT")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(DEFAULT_PORT);

    tracing::info!("chibi-mcp-server v0.2.0-alpha starting on stdio + ws://{host}:{port}");

    // MCP runs as a background task — when Claude Code disconnects the stdio
    // session, we just keep serving the desktop app over WebSocket.
    let _mcp_task = tokio::spawn(async {
        match ChibiMcp::new().serve(stdio()).await {
            Ok(handle) => {
                let _ = handle.waiting().await;
                tracing::info!("mcp stdio session ended");
            }
            Err(e) => tracing::warn!("mcp stdio not available: {e}"),
        }
    });

    // WebSocket runs forever (until SIGINT/SIGTERM).
    let ws_state = Arc::clone(&state);
    let ws_broadcaster = GLOBAL_BROADCASTER.get().unwrap().clone();
    tokio::select! {
        res = ws_server::run_ws_server(&host, port, ws_state, ws_broadcaster) => {
            if let Err(e) = res {
                tracing::error!("ws server error: {e}");
            }
        }
        _ = tokio::signal::ctrl_c() => {
            tracing::info!("ctrl-c received, shutting down");
        }
    }
    Ok(())
}
