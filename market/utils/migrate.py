# coding: utf-8
"""Module providing usefull functions for migrations."""

from django.db import DEFAULT_DB_ALIAS, connections
from django.db.migrations.recorder import MigrationRecorder


def mark_migrated(app, migration):
    """Mark `migration` within an `app` as performed."""
    def _mark_migrated(apps, schema_editor):
        MigrationRecorder(connections[DEFAULT_DB_ALIAS])\
            .record_applied(app, migration)

    return _mark_migrated
