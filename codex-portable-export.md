# Codex portable export

Generated from the current Windows Codex installation on 2026-09-22.

This is a sanitized inventory. It intentionally excludes credentials, notification executables, runtime pipes, machine-specific paths, project trust entries, caches, and conversation history.

## Enabled plugins

### OpenAI bundled

- `codex-app-tools`
- `browser`
- `visualize`
- `unified-computer-use`
- `computer-use`
- `chrome`

### OpenAI primary runtime

- `documents`
- `pdf`
- `spreadsheets`
- `presentations`
- `template-creator`

### Claude plugins official

- `chrome-devtools-mcp`
- `claude-code-setup`
- `code-review`
- `code-simplifier`
- `feature-dev`
- `frontend-design`
- `github`
- `playwright`
- `superpowers`
- `rust-analyzer-lsp`
- `browser-use`

Installed but disabled:

- `remember`

## Installed plugin versions

These are the versions currently present in the local cache. The target machine may resolve newer versions when the marketplaces are refreshed.

- Claude official: `browser-use` `local`, `chrome-devtools-mcp` `1.8.0`, `claude-code-setup` `1.0.0`, `code-review` `local`, `code-simplifier` `1.0.0`, `feature-dev` `local`, `frontend-design` `local`, `github` `local`, `playwright` `local`, `remember` `0.33.0`, `rust-analyzer-lsp` `1.0.0`, `superpowers` `6.3.0`
- OpenAI bundled: `browser` `26.915.31945`, `chrome` `26.915.31945` and `latest`, `codex-app-tools` `0.1.4`, `computer-use` `26.915.31945`, `unified-computer-use` `26.915.31945`, `visualize` `1.0.38`
- OpenAI primary runtime: `documents`, `pdf`, `presentations`, `spreadsheets`, and `template-creator`, all `26.905.11957`
- OpenAI curated remote: `codex-security` `0.1.24`, `engineering-suite-grill-me` `2.0.0`, `github` `0.1.12-5f7cd798dc99`, `openai-templates` `0.1.1`, `plugin-management` `0.1.0`, `superdesign` `0.6.0`, `superpowers` `6.4.1`, plus six installed app plugins with opaque IDs

The curated-remote plugins were installed locally but are not enabled in the active `config.toml` plugin list.

## Custom skills

The user skill directory currently contains:

`ask-matt`, `cavecrew`, `claude-handoff`, `code-review`, `codebase-design`, `diagnosing-bugs`, `domain-modeling`, `find-skills`, `grill-me`, `grill-with-docs`, `grilling`, `handoff`, `implement`, `implement-spec`, `improve-codebase-architecture`, `investigate-first`, `lean-build`, `migration`, `ponytail`, `ponytail-audit`, `ponytail-debt`, `ponytail-gain`, `ponytail-help`, `ponytail-review`, `prototype`, `research`, `resolving-merge-conflicts`, `safe-refactor`, `setup-matt-pocock-skills`, `surgical-patch`, `synced`, `tdd`, `teach`, `to-questionnaire`, `to-spec`, `to-tickets`, `triage`, `verify-and-stop`, `wait-what`, `wayfinder`, `wizard`, and `writing-for-agents`.

Copy the contents of `$HOME/.agents/skills` to the equivalent user skills directory on the other machine if these custom skills are needed.

## Portable settings

The companion file `codex-config.sanitized.toml` contains the portable subset of the current configuration. It preserves model, reasoning, approval, feature, desktop, marketplace, plugin, MCP, and TUI settings while omitting secrets and local paths.

## Setup on another machine

1. Install and sign in to Codex on the target machine.
2. Copy the custom skills directory if required.
3. Add the marketplace sources from `codex-config.sanitized.toml` using paths valid on the target machine.
4. Copy the sanitized settings into the target user's Codex config, adjusting executable paths and removing unsupported settings if the installed Codex version differs.
5. Set `CONTEXT7_API_KEY` and `GITHUB_PAT_TOKEN` in the target machine's environment only if those MCP servers are needed. Do not place credentials directly in the config file.
6. Refresh marketplaces or restart Codex, then verify the enabled plugins in the plugin browser.

OpenAI's official documentation states that user plugin preferences are stored in `~/.codex/config.toml`, while plugin files are installed under the Codex plugin cache. Plugin services may still require separate authentication.
