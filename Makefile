.PHONY: check server-test server-build vscode-package desktop-lint rust-check runtime-check strict-check public-beta-check release-check

check:
	./scripts/verify_all.sh

server-test:
	cd server && python -m ruff check . && python -m pytest -q

server-build:
	cd server && venv/bin/python -m build --wheel && python -m chibi_mcp --check

vscode-package:
	./scripts/package-vscode.sh

desktop-lint:
	cd desktop && npm run lint

rust-check:
	cd server-rs && cargo fmt -- --check && cargo clippy --all-targets -- -D warnings
	./scripts/check-linux-tauri-deps.sh
	cd desktop/src-tauri && cargo fmt -- --check && cargo check --all-targets

runtime-check:
	./scripts/verify_runtime.sh

strict-check:
	CHIBI_STRICT_RUNTIME=1 ./scripts/verify_all.sh

public-beta-check:
	./scripts/public_beta_preflight.sh

release-check:
	./scripts/release_preflight.sh $(TAG)
