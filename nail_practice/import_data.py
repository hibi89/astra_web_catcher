"""One-time isolated import from a practice ZIP; never edits ZIP or existing DB.

No usernames, captions, profile image links, Instagram URLs or media URL values
are copied into the practice SQLite database. Instagram post/media IDs are kept
as opaque strings to preserve foreign keys.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone, timedelta
import io
from pathlib import Path
import sqlite3
import zipfile

SCHEMA = Path(__file__).with_name('schema.sql')
DB_DEFAULT = Path(__file__).parent / 'data' / 'ohora_practice.db'
ZIP_NAME = 'OHORA_Analysis_Ready_20261016_084112.zip'
KST = timezone(timedelta(hours=9))


def source_default() -> Path:
    return Path.home() / 'Downloads' / ZIP_NAME


def rows_from_zip(zf: zipfile.ZipFile, filename: str):
    with zf.open(filename) as fh:
        return list(csv.DictReader(io.TextIOWrapper(fh, encoding='utf-8-sig', newline='')))


def integer(raw):
    return None if raw is None or str(raw).strip() == '' else int(str(raw).strip())


def import_practice(source: str | Path, target: str | Path):
    source, target = Path(source), Path(target)
    if not source.is_file():
        raise FileNotFoundError(f'분석 ZIP 없음: {source}')
    if target.exists():
        raise FileExistsError(f'보존을 위해 기존 실험 DB 덮어쓰기 금지: {target}')
    if source.resolve() == target.resolve():
        raise ValueError('source and target may not match')
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.with_name(target.name + '.importing')
    if staging.exists():
        raise FileExistsError(f'남아 있는 임시 DB 확인 필요: {staging}')
    try:
        with zipfile.ZipFile(source) as z:
            if z.testzip() is not None: raise ValueError('ZIP CRC invalid')
            account_rows = rows_from_zip(z, 'accounts_coverage.csv')
            post_rows = rows_from_zip(z, 'posts_flat_for_analysis.csv')
            media_rows = rows_from_zip(z, 'media_merged.csv')
        if any(not a.get('account_key') for a in account_rows): raise ValueError('missing account keys')
        if any(not p.get('post_id') or not p.get('account_key') for p in post_rows): raise ValueError('missing post keys')
        if any(not m.get('media_id') or not m.get('post_id') for m in media_rows): raise ValueError('missing media keys')
        with sqlite3.connect(staging) as con:
            con.execute('PRAGMA foreign_keys=ON')
            con.executescript(SCHEMA.read_text(encoding='utf-8'))
            con.executemany('INSERT INTO accounts VALUES(?,?,?,?,?,?)', [
                (a['account_key'], a['country'], a['collection_status'], integer(a.get('posts_available')) or 0,
                 integer(a.get('followers_at_collection')), a.get('error_code') or None) for a in account_rows
            ])
            prepared = []
            for p in post_rows:
                timestamp = datetime.fromisoformat(p['posted_at'].replace('Z', '+00:00'))
                if timestamp.tzinfo is None:
                    raise ValueError('Timezone required for reliable hourly chart')
                kst = timestamp.astimezone(KST)
                likes, comments = integer(p.get('likes')), integer(p.get('comments'))
                reaction = None if likes is None or comments is None else likes + comments
                claimed = integer(p.get('engagement_count'))
                if claimed != reaction: raise ValueError('Engagement count mismatch')
                prepared.append((p['post_id'], p['account_key'], p['country'], p['posted_at'],
                      kst.date().isoformat(), kst.hour, p['media_type'],p['media_product_type'],
                      likes,comments,reaction,integer(p.get('followers_at_collection')),
                      integer(p.get('attached_media_rows')) or 0,p['collected_at']))
            con.executemany('INSERT INTO posts VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)', prepared)
            con.executemany('INSERT INTO media VALUES(?,?,?,?)', [
                (m['media_id'],m['post_id'],m['media_type'],m.get('media_role')) for m in media_rows
            ])
            if con.execute('PRAGMA foreign_key_check').fetchall():
                raise ValueError('Broken account/post/media foreign keys')
            if con.execute('SELECT COUNT(*) FROM posts WHERE reactions IS NULL').fetchone()[0] != sum(p[10] is None for p in prepared):
                raise ValueError('Nullable reaction contract failed')
            con.commit()
        # Do not overwrite existing database, even in a race.
        # Hard-link creates only when target does not exist, keeping existing data safe.
        import os
        os.link(staging, target)
        staging.unlink()
        return {'accounts':len(account_rows),'posts':len(prepared),'media':len(media_rows),
                'reactions_available':sum(p[10] is not None for p in prepared),
                'db':str(target),'original_source_unmodified':True}
    except Exception:
        staging.unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description='Read-only source to separate practice SQLite (never overwrite)')
    parser.add_argument('--zip',dest='source',type=Path,default=source_default())
    parser.add_argument('--db',dest='target',type=Path,default=DB_DEFAULT)
    args=parser.parse_args()
    print(import_practice(args.source,args.target))

if __name__=='__main__': main()
