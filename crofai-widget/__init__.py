"""CrofAI TUI widget companion plugin.

Registers:
  - on_session_start hook  → tries to patch _get_extra_tui_widgets
  - post_api_request hook  → fallback (known to fire, for timing comparison)
  - /crofai slash command  → always works, fetches & displays usage
  - hermes crof CLI cmd    → runs TUI with persistent usage widget

The ``hermes crof`` command is the primary way to get the persistent widget —
it subclasses ``HermesCLI`` at import time so the widget is baked into the
TUI layout from the very first render.
"""

from __future__ import annotations

import json
import logging
import os
import time
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

_USAGE_API = "https://crof.ai/usage_api/"
_CACHE: dict = {"data": None, "timestamp": 0.0}


def _bust_cache() -> None:
    """Force the next ``_fetch_usage()`` call to hit the API."""
    _CACHE["timestamp"] = 0.0


# ── Usage API helpers ────────────────────────────────────────────────────


def _fetch_usage(*, force: bool = False) -> dict:
    """Fetch usage stats, cached until the next ``_bust_cache()`` call."""
    now = time.time()
    if not force and _CACHE["data"] is not None and _CACHE["timestamp"] > 0:
        return _CACHE["data"]

    api_key = os.environ.get("CROFAI_API_KEY")
    if not api_key:
        _CACHE["data"] = {"error": "CROFAI_API_KEY not set"}
        _CACHE["timestamp"] = now
        return _CACHE["data"]

    try:
        req = Request(_USAGE_API)
        req.add_header("Authorization", f"Bearer {api_key}")
        req.add_header("User-Agent", "curl/8.4.0")
        with urlopen(req, timeout=5) as resp:
            data: dict = json.loads(resp.read().decode())
            _CACHE["data"] = data
            _CACHE["timestamp"] = now
            return data
    except Exception as exc:
        _CACHE["data"] = {"error": str(exc)}
        _CACHE["timestamp"] = now
        return _CACHE["data"]


# ── TUI widget factory ───────────────────────────────────────────────────


def _build_usage_widget():
    """Return a prompt_toolkit Window showing CrofAI usage stats.

    Content is dynamically generated via a lambda on each redraw, with
    the underlying API call cached to avoid hammering the endpoint.
    """
    from prompt_toolkit.layout import FormattedTextControl, Window

    def _content() -> str:
        usage = _fetch_usage()
        if "error" in usage or not usage:
            return " CrofAI: err "
        credits = usage.get("credits")
        reqs = usage.get("usable_requests")
        if isinstance(credits, (int, float)):
            if reqs is not None:
                return f" CrofAI: ${credits:.2f} \u2502 {int(reqs):,} reqs "
            return f" CrofAI: ${credits:.2f} "
        return " CrofAI: \u2014 "

    return Window(FormattedTextControl(_content), height=1, style="class:status-bar")


# ─── HermesCLI subclass for persistent widget ────────────────────────────


def _make_crofai_cli():
    """Dynamically create a ``HermesCLI`` subclass with the widget baked in."""
    from cli import HermesCLI

    class CrofaiCLI(HermesCLI):
        """Hermes TUI with a persistent CrofAI usage widget in the status bar."""

        _crofai_widget_builtin = True  # marker for hook guards

        def _get_extra_tui_widgets(self):
            return [_build_usage_widget()]

    return CrofaiCLI


# ── CLI subcommand: ``hermes crof`` ──────────────────────────────────────


def _setup_crof_parser(subparser) -> None:
    """Add arguments to the ``hermes crof`` subparser."""
    subparser.add_argument(
        "-m", "--model", default=None,
        help="Model override (e.g. anthropic/claude-sonnet-4.6)",
    )
    subparser.add_argument(
        "--provider", default=None,
        help="Provider override (e.g. openrouter, crofai)",
    )
    subparser.add_argument(
        "-t", "--toolsets", default=None,
        help="Comma-separated toolsets to enable",
    )
    subparser.add_argument(
        "--skills", default=None, nargs="*",
        help="Skills to preload for the session",
    )
    subparser.add_argument(
        "-q", "--query", default=None,
        help="Single query to execute (then exit)",
    )
    subparser.add_argument(
        "--image", default=None,
        help="Local image path to attach to a single query",
    )
    subparser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging",
    )
    subparser.add_argument(
        "--quiet", action="store_true", help="Suppress non-essential output",
    )
    subparser.add_argument(
        "-c", "--continue", dest="continue_last", default=None,
        nargs="?", const=True,
        help="Resume the most recent session (or a session by name/ID)",
    )
    subparser.add_argument(
        "--resume", default=None,
        help="Resume a specific session by ID",
    )
    subparser.add_argument(
        "-w", "--worktree", action="store_true",
        help="Run in an isolated git worktree",
    )
    subparser.add_argument(
        "--checkpoints", action="store_true",
        help="Enable checkpointing for the session",
    )
    subparser.add_argument(
        "--max-turns", type=int, default=None,
        help="Maximum tool-calling iterations",
    )
    subparser.add_argument(
        "--ignore-rules", action="store_true",
        help="Skip AGENTS.md / CLAUDE.md / .cursorrules loading",
    )
    subparser.add_argument(
        "--ignore-user-config", action="store_true",
        help="Skip user config loading",
    )


def _handle_crof_cli(args) -> None:
    """Run the Hermes TUI with the CrofAI usage widget displayed.

    Monkey-patches ``cli.HermesCLI`` with ``CrofaiCLI`` (a subclass that
    overrides ``_get_extra_tui_widgets``) so the widget is baked into the
    TUI layout at build time — no hook timing issues.
    """
    import cli as cli_mod

    # Swap HermesCLI for our subclass
    CrofaiCLI = _make_crofai_cli()
    original = cli_mod.HermesCLI
    cli_mod.HermesCLI = CrofaiCLI

    # Resolve --continue into --resume (same logic as cmd_chat)
    resume_val = getattr(args, "resume", None)
    continue_val = getattr(args, "continue_last", None)
    if continue_val and not resume_val:
        if isinstance(continue_val, str):
            args.resume = continue_val
        else:
            # -c with no argument — find the last CLI session
            from hermes_cli.main import _resolve_last_session
            last_id = _resolve_last_session(source="cli")
            if last_id:
                args.resume = last_id

    # Build kwargs matching cli.main() signature
    kwargs = {k: getattr(args, k, None) for k in (
        "model", "provider", "toolsets", "skills", "verbose", "quiet",
        "query", "image", "resume", "worktree", "checkpoints",
        "max_turns", "ignore_rules", "ignore_user_config",
    )}
    kwargs = {k: v for k, v in kwargs.items() if v is not None}

    try:
        cli_mod.main(**kwargs)
    finally:
        cli_mod.HermesCLI = original


# ── Layout injection helpers (hook-based, for comparison) ────────────────


def _patch_get_extra_widgets(cli) -> bool:
    """Monkey-patch ``_get_extra_tui_widgets`` to append our widget."""
    original = cli._get_extra_tui_widgets

    def _patched():
        existing = original() if callable(original) else []
        if not isinstance(existing, (list, tuple)):
            existing = []
        return list(existing) + [_build_usage_widget()]

    cli._get_extra_tui_widgets = _patched
    logger.info("crofai-widget: monkey-patched cli._get_extra_tui_widgets")
    return True


def _patch_hsplit_children(cli) -> bool:
    """Directly insert our widget into the HSplit children list.

    This is fragile but bypasses the layout-build-time limitation of
    monkey-patching _get_extra_tui_widgets.
    """
    try:
        app = getattr(cli, "_app", None)
        if app is None:
            logger.debug("crofai-widget: cli._app is None, skipping HSplit patch")
            return False
        container = app.layout.container
        if container is None:
            logger.debug("crofai-widget: app.layout.container is None")
            return False
        if not hasattr(container, "children"):
            logger.debug("crofai-widget: container has no .children (type=%s)", type(container).__name__)
            return False

        children = container.children
        if len(children) > 5:
            widget = _build_usage_widget()
            children.insert(-5, widget)
            logger.info(
                "crofai-widget: inserted widget into HSplit.children "
                "(len before=%d, inserted at -5)",
                len(children),
            )
            return True

        logger.debug("crofai-widget: too few children (%d) to insert", len(children))
        return False
    except Exception as exc:
        logger.warning("crofai-widget: HSplit patch failed: %s", exc)
        return False


def _inject_tui_widget(cli) -> bool:
    """Try both injection strategies."""
    if cli is None:
        logger.info("crofai-widget: _inject_tui_widget — cli is None, nothing to do")
        return False

    monkey_ok = _patch_get_extra_widgets(cli)
    hsplit_ok = _patch_hsplit_children(cli)

    try:
        cli._invalidate()
    except Exception:
        pass

    return monkey_ok or hsplit_ok


# ── Hook handlers (debug comparison vs subclass approach) ────────────────


def _on_session_start(**kwargs: object) -> None:
    """Debug hook: fires when a new session starts."""
    from hermes_cli.plugins import get_plugin_manager

    mgr = get_plugin_manager()
    cli = mgr._cli_ref

    logger.info(
        "crofai-widget: on_session_start FIRED.  kwargs_keys=%s  _cli_ref=%s  "
        "_cli_ref_type=%s",
        list(kwargs.keys()),
        cli is not None,
        type(cli).__name__ if cli else "N/A",
    )

    if cli is None:
        return

    # Skip if the subclass already bakes the widget in
    if getattr(cli, "_crofai_widget_builtin", False):
        logger.info("crofai-widget: on_session_start — skipping (CrofaiCLI subclass)")
        return

    if getattr(cli, "_crofai_widget_injected", False):
        return

    ok = _patch_get_extra_widgets(cli)
    cli._crofai_widget_injected = ok
    logger.info("crofai-widget: on_session_start → inject=%s", ok)


def _post_api_request(**kwargs: object) -> None:
    """Fallback: fires after every LLM API call."""
    from hermes_cli.plugins import get_plugin_manager

    mgr = get_plugin_manager()
    cli = mgr._cli_ref

    if getattr(cli, "_crofai_widget_injected", False):
        return

    # Skip if the subclass already bakes the widget in
    if getattr(cli, "_crofai_widget_builtin", False):
        return

    logger.info(
        "crofai-widget: post_api_request FIRED (fallback).  "
        "kwargs_keys=%s  _cli_ref=%s",
        list(kwargs.keys()),
        cli is not None,
    )

    if cli is None:
        return

    ok = _patch_get_extra_widgets(cli)
    cli._crofai_widget_injected = ok
    logger.info("crofai-widget: post_api_request fallback → inject=%s", ok)


def _post_api_request_bust_cache(**kwargs: object) -> None:
    """Bust the usage cache after each API call so the widget stays current."""
    _bust_cache()


# ── Slash command handler ────────────────────────────────────────────────


def _handle_crofai(raw_args: str) -> str | None:
    """``/crofai`` — show CrofAI usage stats."""
    usage = _fetch_usage(force=True)

    if "error" in usage:
        return f" CrofAI usage error: {usage['error']}"

    credits = usage.get("credits")
    reqs = usage.get("usable_requests")

    lines = ["\u256d\u2500 CrofAI Usage \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u256e"]
    if isinstance(credits, (int, float)):
        lines.append(f"\u2502 Credits:        ${credits:<8.2f}\u2502")
    else:
        lines.append(f"\u2502 Credits:        {str(credits):<9}\u2502")
    if reqs is not None:
        lines.append(f"\u2502 Usable requests: {int(reqs):<9,}\u2502")
    else:
        lines.append("\u2502 Plan:           subscription  \u2502")
    lines.append("\u2570\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u256f")
    return "\n".join(lines)


# ── Plugin entry point ───────────────────────────────────────────────────


def register(ctx) -> None:
    """Register this plugin with Hermes."""
    ctx.register_hook("on_session_start", _on_session_start)
    ctx.register_hook("post_api_request", _post_api_request)
    ctx.register_hook("post_api_request", _post_api_request_bust_cache)
    ctx.register_command(
        "crofai",
        handler=_handle_crofai,
        description="Show CrofAI usage stats (credits, requests)",
    )
    ctx.register_cli_command(
        "crof",
        help="Run TUI with CrofAI usage widget",
        description="Run the Hermes interactive TUI with a persistent CrofAI usage "
                    "widget showing live credits and request counts.",
        setup_fn=_setup_crof_parser,
        handler_fn=_handle_crof_cli,
    )
    logger.info(
        "crofai-widget: registered — on_session_start, post_api_request, "
        "/crofai, hermes crof"
    )
