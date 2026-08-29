"""Backfill Block K.1 settings on sites that already ran the base defaults patch."""

from tecponto_app.patches.v16_0.initialize_operation_settings_defaults import execute as initialize_defaults


def execute() -> None:
	initialize_defaults()
