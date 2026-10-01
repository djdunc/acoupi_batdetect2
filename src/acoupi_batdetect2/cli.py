"""CLI wrapper for Acoupi to persist and reuse deployment defaults."""

import json
from pathlib import Path

import click
from acoupi.cli.base import acoupi as original_acoupi

DEFAULTS_FILE = (
    Path.home() / ".acoupi" / "config" / "deployment_defaults.json"
)


def get_defaults():
    """Retrieve saved deployment defaults from file."""
    if DEFAULTS_FILE.exists():
        try:
            with open(DEFAULTS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_defaults(name, latitude, longitude):
    """Save deployment defaults to file."""
    try:
        DEFAULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(DEFAULTS_FILE, "w") as f:
            json.dump(
                {
                    "name": name,
                    "latitude": latitude,
                    "longitude": longitude,
                },
                f,
                indent=4,
            )
    except Exception:
        pass


# Wrap the main group callback to inject default_map
original_group_callback = original_acoupi.callback


def custom_group_callback(ctx, *args, **kwargs):
    defaults = get_defaults()
    if defaults:
        ctx.default_map = {"deployment": {"start": defaults}}
    if original_group_callback:
        return original_group_callback(*args, **kwargs)


original_acoupi.callback = click.pass_context(custom_group_callback)

# Intercept and wrap the start command callback to save the inputs
try:
    deployment_group = original_acoupi.commands.get("deployment")
    if deployment_group:
        start_cmd = deployment_group.commands.get("start")
        if start_cmd:
            original_callback = start_cmd.callback

            def custom_callback(*args, **kwargs):
                name = kwargs.get("name")
                latitude = kwargs.get("latitude")
                longitude = kwargs.get("longitude")
                save_defaults(name, latitude, longitude)
                if original_callback:
                    return original_callback(*args, **kwargs)

            start_cmd.callback = custom_callback
except Exception:
    pass

main = original_acoupi
