"""CrofAI usage widget companion plugin for Hermes.

Provides:
  - ``hermes crof``: starts the prompt_toolkit TUI with a persistent CrofAI
    usage widget baked into the layout via a ``HermesCLI`` subclass.
  - ``/crofai``: shows current credits and usable requests on demand.
  - ``post_api_request`` hook: schedules a delayed usage refresh after model calls.
"""

from __future__ import annotations

import json
import logging
import os
import time
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

_USAGE_API = "https://crof.ai/usage_api/"
_REFRESH_DELAY_SECONDS = 1.0
_usage_cache: dict | None = None
_refresh_after = 0.0


def _schedule_refresh(delay: float = _REFRESH_DELAY_SECONDS) -> None:
    """Refresh usage on the next widget redraw after ``delay`` seconds.

    CrofAI usage stats can lag slightly behind the completed API call, so the
    hook schedules a delayed refresh instead of fetching immediately.
    """
    global _refresh_after
    _refresh_after = time.time() + delay


def _fetch_usage(*, force: bool = False) -> dict:
    """Fetch CrofAI usage, cached until a scheduled refresh becomes due."""
    global _usage_cache, _refresh_after

    now = time.time()
    refresh_due = bool(_refresh_after and now >= _refresh_after)
    if not force and _usage_cache is not None and not refresh_due:
        return _usage_cache

    api_key = os.environ.get("CROFAI_API_KEY")
    if not api_key:
        _usage_cache = {"error": "CROFAI_API_KEY not set"}
        _refresh_after = 0.0
        return _usage_cache

    try:
        req = Request(_USAGE_API)
        req.add_header("Authorization", f"Bearer {api_key}")
        # crof.ai/Cloudflare blocks Python urllib's default User-Agent.
        req.add_header("User-Agent", "curl/8.4.0")
        with urlopen(req, timeout=5) as resp:
            _usage_cache = json.loads(resp.read().decode())
    except Exception as exc:
        _usage_cache = {"error": str(exc)}

    _refresh_after = 0.0
    return _usage_cache or {"error": "empty usage response"}


def _format_inline_usage() -> str:
    """Format one-line widget text."""
    usage = _fetch_usage()
    if not usage or "error" in usage:
        return " CrofAI: err "

    credits = usage.get("credits")
    reqs = usage.get("usable_requests")
    if isinstance(credits, (int, float)):
        if reqs is not None:
            return f" CrofAI: ${credits:.3f} │ {int(reqs):,} reqs "
        return f" CrofAI: ${credits:.3f} "
    return " CrofAI: — "


def _build_usage_widget():
    """Return a prompt_toolkit status-row widget for CrofAI usage."""
    from prompt_toolkit.layout import FormattedTextControl, Window

    return Window(
        FormattedTextControl(_format_inline_usage),
        height=1,
        style="class:status-bar",
    )


def _make_crofai_cli():
    """Create a ``HermesCLI`` subclass with the usage widget baked in."""
    from cli import HermesCLI

    class CrofaiCLI(HermesCLI):
        def _get_extra_tui_widgets(self):
            return [_build_usage_widget()]

    return CrofaiCLI


def _setup_crof_parser(subparser) -> None:
    """Add chat-like flags to the ``hermes crof`` subcommand."""
    for flags, kwargs in [
        (("-m", "--model"), {"help": "Model override"}),
        (("--provider",), {"help": "Provider override"}),
        (("-t", "--toolsets"), {"help": "Comma-separated toolsets to enable"}),
        (("--skills",), {"nargs": "*", "help": "Skills to preload"}),
        (("-q", "--query"), {"help": "Single query to execute, then exit"}),
        (("--image",), {"help": "Local image path to attach to a single query"}),
        (("-v", "--verbose"), {"action": "store_true", "help": "Enable verbose logging"}),
        (("--quiet",), {"action": "store_true", "help": "Suppress non-essential output"}),
        (("--resume",), {"help": "Resume a specific session by ID"}),
        (("-w", "--worktree"), {"action": "store_true", "help": "Run in an isolated git worktree"}),
        (("--checkpoints",), {"action": "store_true", "help": "Enable checkpointing"}),
        (("--max-turns",), {"type": int, "help": "Maximum tool-calling iterations"}),
        (("--ignore-rules",), {"action": "store_true", "help": "Skip project rule files"}),
        (("--ignore-user-config",), {"action": "store_true", "help": "Skip user config loading"}),
    ]:
        subparser.add_argument(*flags, default=None, **kwargs)

    subparser.add_argument(
        "-c", "--continue",
        dest="continue_last",
        nargs="?",
        const=True,
        default=None,
        help="Resume the most recent session, or a session by name/ID",
    )


def _resolve_continue(args) -> None:
    """Translate ``hermes crof -c`` into ``args.resume`` like ``hermes chat``."""
    if getattr(args, "resume", None) or not getattr(args, "continue_last", None):
        return

    if isinstance(args.continue_last, str):
        args.resume = args.continue_last
        return

    # Dynamic import keeps this plugin importable in Hermes versions where the
    # helper path changes; this branch only runs for `hermes crof -c`.
    from importlib import import_module

    main_mod = import_module("hermes_cli.main")
    if last_id := main_mod._resolve_last_session(source="cli"):
        args.resume = last_id


def _handle_crof_cli(args) -> None:
    """Run Hermes with ``HermesCLI`` temporarily replaced by ``CrofaiCLI``."""
    import cli as cli_mod

    _resolve_continue(args)

    kwargs = {
        name: value
        for name in (
            "model", "provider", "toolsets", "skills", "verbose", "quiet",
            "query", "image", "resume", "worktree", "checkpoints",
            "max_turns", "ignore_rules", "ignore_user_config",
        )
        if (value := getattr(args, name, None)) is not None
    }

    original = cli_mod.HermesCLI
    cli_mod.HermesCLI = _make_crofai_cli()
    try:
        cli_mod.main(**kwargs)
    finally:
        cli_mod.HermesCLI = original


def _handle_crofai(raw_args: str) -> str | None:
    """``/crofai`` — show live CrofAI usage stats."""
    usage = _fetch_usage(force=True)
    if "error" in usage:
        return f" CrofAI usage error: {usage['error']}"

    credits = usage.get("credits")
    reqs = usage.get("usable_requests")
    credit_text = f"${credits:.2f}" if isinstance(credits, (int, float)) else str(credits)
    req_text = f"{int(reqs):,}" if reqs is not None else "subscription"

    return "\n".join([
        "╭─ CrofAI Usage ─────────────╮",
        f"│ Credits:        {credit_text:<9}│",
        f"│ Usable requests: {req_text:<9}│",
        "╰────────────────────────────╯",
    ])


def register(ctx) -> None:
    """Register hooks, slash command, and ``hermes crof`` subcommand."""
    ctx.register_hook("post_api_request", lambda **_: _schedule_refresh())
    ctx.register_command(
        "crofai",
        handler=_handle_crofai,
        description="Show CrofAI usage stats (credits, requests)",
    )
    ctx.register_cli_command(
        "crof",
        help="Run TUI with CrofAI usage widget",
        description="Run Hermes TUI with a persistent CrofAI usage widget.",
        setup_fn=_setup_crof_parser,
        handler_fn=_handle_crof_cli,
    )
    logger.info("crofai-widget: registered — /crofai, hermes crof, post_api_request")
