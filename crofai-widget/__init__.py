"""CrofAI TUI widget companion plugin.

Registers:
  - on_session_start hook  → tries to patch _get_extra_tui_widgets
  - post_api_request hook  → fallback (known to fire, for timing comparison)
  - /crofai slash command  → always works, fetches & displays usage

This plugin exists to test whether on_session_start fires in the Hermes CLI
TUI at a time when _cli_ref is available for TUI layout monkey-patching.
"""

from __future__ import annotations

import json
import logging
import os
import time
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

_USAGE_API = "https://crof.ai/usage_api/"
_CACHE: dict = {"data": None, "timestamp": 0.0, "ttl": 60}


# ── Usage API helpers ────────────────────────────────────────────────────


def _fetch_usage(*, force: bool = False) -> dict:
    """Fetch usage stats, cached for ``_CACHE["ttl"]`` seconds."""
    now = time.time()
    if not force and _CACHE["data"] and (now - _CACHE["timestamp"] < _CACHE["ttl"]):
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
        return " CrofAI: — "

    return Window(FormattedTextControl(_content), height=1, style="class:status-bar")


# ── Layout injection helpers ─────────────────────────────────────────────


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
        # Insert just before the status bar (which is the first child after
        # the spacer in _build_tui_layout_children's default order). Walk
        # backwards to find it.
        insert_before = None
        for idx, child in enumerate(children):
            style = getattr(getattr(child, "style", None), "name", "") if hasattr(child, "style") else ""
            # crude heuristic: status bar is usually a Window with
            # style containing "status". We look for it by position —
            # it's after the spacer in the default layout.
            pass

        # Simplest heuristic: insert before last 5 children
        # (status_bar, input_rule_top, image_bar, input_area, ...)
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

    # Trigger redraw
    try:
        cli._invalidate()
    except Exception:
        pass

    return monkey_ok or hsplit_ok


# ── Hook handlers ────────────────────────────────────────────────────────


def _on_session_start(**kwargs: object) -> None:
    """Fired (theoretically) when a conversation session starts.

    We attempt TUI widget injection and log everything for debug.
    """
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

    if getattr(cli, "_crofai_widget_injected", False):
        return

    ok = _inject_tui_widget(cli)
    cli._crofai_widget_injected = ok
    logger.info("crofai-widget: on_session_start → inject=%s", ok)


def _post_api_request(**kwargs: object) -> None:
    """Fallback: fires after every LLM API call — definitely works.

    Used as a timing comparison against on_session_start.
    """
    from hermes_cli.plugins import get_plugin_manager

    mgr = get_plugin_manager()
    cli = mgr._cli_ref

    # Only attempt injection once
    if getattr(cli, "_crofai_widget_injected", False):
        return

    logger.info(
        "crofai-widget: post_api_request FIRED (fallback).  "
        "kwargs_keys=%s  _cli_ref=%s",
        list(kwargs.keys()),
        cli is not None,
    )

    if cli is None:
        return

    ok = _inject_tui_widget(cli)
    cli._crofai_widget_injected = ok
    logger.info("crofai-widget: post_api_request fallback → inject=%s", ok)


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
    ctx.register_command(
        "crofai",
        handler=_handle_crofai,
        description="Show CrofAI usage stats (credits, requests)",
    )
    logger.info(
        "crofai-widget: registered — on_session_start, post_api_request, /crofai"
    )
