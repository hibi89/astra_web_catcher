"""Review-only bridge from ASTRA's pinned fictional DDL to declared schema metadata.

Uses a byte-pinned, repository-local migration in an IN-MEMORY SQLite connection.
Never opens a user DB, reads rows, writes output, infers field semantics or grants
approval. The digest pin must be reviewed, not silently updated, after DDL changes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

RELATIVE_MIGRATION = Path('migrations/001_initial.sql')
EXPECTED_GIT_BLOB = '5f5bdcb950dcfa0587b0deec2b7afb5e17f155bd'
EXPOSED = {
    'categories': ('id', 'name'),
    'products': ('id', 'category_id', 'title', 'author', 'description', 'price', 'stock'),
    'companies': ('id', 'name', 'about'),
    'job_postings': ('id', 'company_id', 'title', 'role', 'region',
                     'min_years', 'max_years', 'career_any', 'body', 'is_closed'),
}
ALL_TABLE_COUNT = 11


def _migration(root: Path) -> bytes:
    """Refuse missing, tampered, symlinked or relocated DDL."""
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError('root must be an existing directory')
    parent = root / RELATIVE_MIGRATION.parent
    target = root / RELATIVE_MIGRATION
    if parent.is_symlink() or target.is_symlink() or not target.is_file():
        raise ValueError('migration absent or symlinked')
    if target.stat().st_size > 32768:
        raise ValueError('migration too large')
    raw = target.read_bytes()
    blob = hashlib.sha1(b'blob %d\0' % len(raw) + raw).hexdigest()
    if blob != EXPECTED_GIT_BLOB:
        raise ValueError('pinned migration Git blob mismatch; manual review required')
    return raw


def _sqlite_type(declared: str) -> str:
    if declared.upper() == 'INTEGER':
        return 'integer'
    if declared.upper() == 'TEXT':
        return 'string'
    raise ValueError('unsupported SQLite storage type; no coercion allowed')


def inspect_repository_schema(root: Path) -> dict:
    raw = _migration(root)
    # The fixed hash prevents unreviewed SQL execution. Only an in-memory DB exists.
    with sqlite3.connect(':memory:') as con:
        con.enable_load_extension(False)
        con.executescript(raw.decode('utf-8', 'strict'))
        rows = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
        discovered = {row[0] for row in rows}
        if len(discovered) != ALL_TABLE_COUNT or not set(EXPOSED).issubset(discovered):
            raise ValueError('unexpected schema shape; stop before producing review metadata')
        resources = []
        for table, expected_columns in EXPOSED.items():
            # Table identifiers are hardcoded above, never derived from input.
            columns = con.execute(f'PRAGMA table_info("{table}")').fetchall()
            names = tuple(col[1] for col in columns)
            if names != expected_columns:
                raise ValueError('approved demonstration column layout drift')
            fields = [{
                'name': col[1], 'data_type': _sqlite_type(col[2]),
                'nullable': bool(not col[3] and not col[5]),
            } for col in columns]
            resources.append({'id':table, 'kind':'db_table', 'fields':fields})
    # The existing OwnedSchemaDeclaration accepts exactly these names and types.
    declaration = {
        'schema_version':'0.1', 'source_kind':'synthetic_fixture',
        'source_label':'ASTRA fictional BookHarbor/CareerWay repository DDL (not live DB)',
        'resources':resources, 'bindings':[],
    }
    return {
        'report_version':'0.1', 'status':'offline_static_schema_inspected_review_only',
        'source_path':RELATIVE_MIGRATION.as_posix(),
        'source_git_blob_sha1': EXPECTED_GIT_BLOB,
        'source_sha256':hashlib.sha256(raw).hexdigest(),
        'table_count_in_static_ddl': len(discovered),
        'exposed_resource_count':len(resources),
        'excluded_resource_count':len(discovered)-len(resources),
        'declaration':declaration,
        'no_row_data_accessed':True,
        'source_is_fictional_application_schema':True,
        'live_database_schema_verified':False,
        'customer_database_accessed':False,
        'original_site_behavior_verified':False,
        'mapping_semantics_verified':False,
        'authorization_granted':False,
        'generation_authorized':False,
        'deployment_authorized':False,
        'external_network_used':False,
        'files_written':False,
        'generation_contract':'blocked_pending_review',
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Offline static DDL→schema review (no live DB connections)')
    parser.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    try:
        report = inspect_repository_schema(args.repo_root)
    except (ValueError, OSError, UnicodeError, sqlite3.Error) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
