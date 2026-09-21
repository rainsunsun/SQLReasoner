"""加载真实 GitHub 事件数据（GH Archive）到 DuckDB。

GH Archive 每小时归档一次全 GitHub 的公开事件（Push/Issue/PR/Watch 等），
公开可下载、无 API 限流。这里拉取真实事件流，解析成一张 events 表，
作为多 agent 数据分析系统的真实数据源（避免 toy 数据的质疑）。

用法：
    python data/load_data.py --date 2026-09-01 --hours 2
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path

import duckdb
import requests

# 让 `python data/load_data.py` 能直接跑：把项目根目录加入 sys.path，才能 import app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config

GH_ARCHIVE = "https://data.gharchive.org/{date}-{hour}.json.gz"


def download(date: str, hour: int, dest: Path) -> Path:
    url = GH_ARCHIVE.format(date=date, hour=hour)
    print(f"  下载 {url} ...")
    r = requests.get(url, timeout=180)
    r.raise_for_status()
    dest.write_bytes(r.content)
    print(f"    已保存 {dest.name} ({len(r.content):,} bytes)")
    return dest


def parse_events(path: Path) -> list[dict]:
    """逐行解析 gzip 的 JSON 事件流，抽取分析关心的字段。"""
    rows: list[dict] = []
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            payload = e.get("payload") or {}
            rows.append(
                {
                    "id": e.get("id"),
                    "type": e.get("type"),
                    "actor_login": (e.get("actor") or {}).get("login"),
                    "repo_name": (e.get("repo") or {}).get("name"),
                    "created_at": e.get("created_at"),
                    "action": payload.get("action"),
                    "payload": json.dumps(payload, ensure_ascii=False),
                }
            )
    return rows


def load(rows: list[dict], db_path: Path) -> None:
    con = duckdb.connect(str(db_path))
    # 显式定义列类型，避免 None 值导致类型推断不稳
    con.execute(
        """
        CREATE OR REPLACE TABLE events (
            id VARCHAR,
            type VARCHAR,
            actor_login VARCHAR,
            repo_name VARCHAR,
            created_at TIMESTAMP,
            action VARCHAR,
            payload VARCHAR
        )
        """
    )
    con.executemany(
        "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (
                r["id"],
                r["type"],
                r["actor_login"],
                r["repo_name"],
                r["created_at"],
                r["action"],
                r["payload"],
            )
            for r in rows
        ],
    )
    # 派生维度表：为 schema linking 提供真实多表结构（repos/actors 从 events 去重）
    con.execute(
        """
        CREATE OR REPLACE TABLE repos AS
        SELECT DISTINCT
            repo_name AS name,
            split_part(repo_name, '/', 1) AS owner,
            split_part(repo_name, '/', 2) AS repo
        FROM events WHERE repo_name IS NOT NULL
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE actors AS
        SELECT DISTINCT actor_login AS login
        FROM events WHERE actor_login IS NOT NULL
        """
    )

    n = con.execute("SELECT count(*) FROM events").fetchone()[0]
    print(f"\n=== 已加载 {n:,} 条真实事件到 {db_path.name} ===")
    print("事件类型分布（Top 10）：")
    for t, c in con.execute(
        "SELECT type, count(*) c FROM events GROUP BY type ORDER BY c DESC LIMIT 10"
    ).fetchall():
        print(f"  {t:22s} {c:>8,}")
    con.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2026-09-01", help="YYYY-MM-DD")
    ap.add_argument("--hours", type=int, default=2, help="拉取的小时数（从 0 点开始）")
    args = ap.parse_args()

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    raw_dir = config.DATA_DIR / "raw"
    raw_dir.mkdir(exist_ok=True)

    all_rows: list[dict] = []
    for hour in range(args.hours):
        dest = raw_dir / f"{args.date}-{hour}.json.gz"
        if not dest.exists():
            download(args.date, hour, dest)
        all_rows.extend(parse_events(dest))

    load(all_rows, config.DB_PATH)


if __name__ == "__main__":
    main()
