"""MultiAgent 看板管理 CLI 工具
支持三个子命令：
  export   — 从 SQLite 导出看板结构为 JSON 文件
  import   — 从 JSON 文件导入看板到 SQLite（带备份）
  migrate  — 数据库间迁移看板数据（含卡片、日志、审批）
"""
import sqlite3
import os
import sys
import shutil
import json
import uuid
import argparse
from datetime import datetime, timezone


def connect(db_path):
    if not os.path.exists(db_path):
        print(f'[错误] 数据库不存在: {db_path}')
        sys.exit(1)
    conn = sqlite3.connect(db_path)
    conn.row_factory = lambda c, r: {col[0]: r[idx] for idx, col in enumerate(c.description)}
    return conn


def backup_db(db_path):
    """备份目标数据库到同目录下的 .bak 文件"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    bak_path = db_path.replace('.db', f'_{timestamp}.bak')
    shutil.copy2(db_path, bak_path)
    print(f'备份: {bak_path} ({os.path.getsize(bak_path)} bytes)')
    return bak_path


def get_columns(cur, table):
    cur.execute(f'PRAGMA table_info({table})')
    return [r['name'] for r in cur.fetchall()]


def copy_rows(src_cur, tgt_cur, table, where_col=None, where_val=None):
    """从源库复制数据到目标库"""
    if where_col and where_val is not None:
        src_cur.execute(f'SELECT * FROM {table} WHERE {where_col} = ?', (where_val,))
    else:
        src_cur.execute(f'SELECT * FROM {table}')

    rows = src_cur.fetchall()
    if not rows:
        return 0

    cols = get_columns(src_cur, table)
    placeholders = ','.join(['?' for _ in cols])
    col_names = ','.join(cols)

    copied = 0
    for row in rows:
        values = [row[col] for col in cols]
        try:
            tgt_cur.execute(f'INSERT INTO {table} ({col_names}) VALUES ({placeholders})', values)
            copied += 1
        except Exception as e:
            if 'UNIQUE' in str(e):
                pass
            else:
                raise
    return copied


# === export ===

def cmd_export(args):
    """导出看板配置为 JSON 文件"""
    src_db = os.path.join(os.path.dirname(__file__), 'backend', 'data', 'multiagent.db')
    conn = connect(src_db)
    cur = conn.cursor()

    cur.execute('SELECT name, description FROM kanbans WHERE id = ?', (args.kanban_id,))
    kanban_row = cur.fetchone()
    if not kanban_row:
        print(f'[错误] 看板不存在: {args.kanban_id}')
        conn.close()
        return

    cur.execute(
        'SELECT name, sort_order, prompt, skill, tools, flow_mode, '
        'local_path, wait_for_reply, local_path_permission, allowed_paths '
        'FROM swimlanes WHERE kanban_id = ? ORDER BY sort_order',
        (args.kanban_id,)
    )
    swimlane_rows = cur.fetchall()
    conn.close()

    data = {
        "version": 1,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "kanban": {
            "name": kanban_row['name'],
            "description": kanban_row['description'] or "",
        },
        "swimlanes": [
            {
                "name": r['name'],
                "sort_order": r['sort_order'],
                "prompt": r['prompt'] or "",
                "skill": r['skill'],
                "tools": r['tools'] or "[]",
                "flow_mode": r['flow_mode'],
                "local_path": r['local_path'],
                "wait_for_reply": r['wait_for_reply'] or "1",
                "local_path_permission": r['local_path_permission'] or "read_write",
                "allowed_paths": r['allowed_paths'] or "[]",
            }
            for r in swimlane_rows
        ],
    }

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f'导出成功: {args.output}')
    else:
        # 默认输出到当前目录
        default_name = f'kanban-{args.kanban_id[:8]}.json'
        with open(default_name, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f'导出成功: {default_name}')


# === import ===

def cmd_import(args):
    """从 JSON 文件导入看板"""
    if os.path.isdir(args.db):
        args.db = os.path.join(args.db, 'multiagent.db')

    if not os.path.exists(args.json_path):
        print(f'[错误] JSON 文件不存在: {args.json_path}')
        return

    with open(args.json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if data.get('version') != 1:
        print(f'[错误] 不支持的导出版本: {data.get("version")}')
        return

    # 备份目标库
    backup_db(args.db)

    conn = connect(args.db)
    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()

    try:
        kanban_id = str(uuid.uuid4())
        kb = data['kanban']
        cur.execute(
            'INSERT INTO kanbans (id, name, description, created_at, updated_at) '
            'VALUES (?, ?, ?, ?, ?)',
            (kanban_id, kb['name'], kb.get('description', ''), now, now),
        )

        sort_order = 0
        for sl in data.get('swimlanes', []):
            sl_id = str(uuid.uuid4())
            cur.execute(
                'INSERT INTO swimlanes '
                '(id, kanban_id, name, sort_order, prompt, skill, tools, flow_mode, '
                'local_path, wait_for_reply, local_path_permission, allowed_paths, '
                'created_at, updated_at) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (
                    sl_id, kanban_id,
                    sl.get('name', ''),
                    sl.get('sort_order', sort_order),
                    sl.get('prompt', ''),
                    sl.get('skill'),
                    sl.get('tools', '[]'),
                    sl.get('flow_mode', 'auto'),
                    sl.get('local_path'),
                    sl.get('wait_for_reply', '1'),
                    sl.get('local_path_permission', 'read_write'),
                    sl.get('allowed_paths', '[]'),
                    now, now,
                ),
            )
            sort_order += 1

        conn.commit()
        print(f'导入成功: 看板「{kb["name"]}」(id={kanban_id}), '
              f'{len(data.get("swimlanes", []))} 个泳道')

    except Exception as e:
        conn.rollback()
        print(f'[错误] {e}')
        raise
    finally:
        conn.close()


# === migrate ===

def cmd_migrate(args):
    """数据库间迁移看板数据（含卡片、日志、审批）"""
    if os.path.isdir(args.target):
        args.target = os.path.join(args.target, 'multiagent.db')
    if os.path.isdir(args.source):
        args.source = os.path.join(args.source, 'multiagent.db')

    print(f'源:   {args.source}')
    print(f'目标: {args.target}')

    backup_db(args.target)

    src = connect(args.source)
    tgt = connect(args.target)
    sc, tc = src.cursor(), tgt.cursor()

    try:
        # 1. kanban
        n = copy_rows(sc, tc, 'kanbans', 'id', args.kanban_id)
        print(f'kanbans: {n} 条')

        # 2. swimlanes
        n = copy_rows(sc, tc, 'swimlanes', 'kanban_id', args.kanban_id)
        print(f'swimlanes: {n} 条')

        # 3. cards
        sc.execute('SELECT id FROM cards WHERE kanban_id = ?', (args.kanban_id,))
        card_ids = [r['id'] for r in sc.fetchall()]
        n = copy_rows(sc, tc, 'cards', 'kanban_id', args.kanban_id)
        print(f'cards: {n} 条')

        # 4. logs
        total_logs = 0
        for cid in card_ids:
            total_logs += copy_rows(sc, tc, 'logs', 'card_id', cid)
        print(f'logs: {total_logs} 条')

        # 5. approvals
        total_app = 0
        for cid in card_ids:
            total_app += copy_rows(sc, tc, 'approvals', 'card_id', cid)
        print(f'approvals: {total_app} 条')

        tgt.commit()
        print(f'\n迁移完成，共 5 张表的数据已同步。')

    except Exception as e:
        tgt.rollback()
        print(f'\n[错误] {e}')
        raise
    finally:
        src.close()
        tgt.close()


# === CLI ===

def main():
    parser = argparse.ArgumentParser(description='MultiAgent 看板管理工具')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # export
    ep = subparsers.add_parser('export', help='导出看板结构为 JSON')
    ep.add_argument('kanban_id', help='看板 ID')
    ep.add_argument('--output', '-o', help='输出文件路径（默认当前目录）')

    # import
    ip = subparsers.add_parser('import', help='从 JSON 文件导入看板')
    ip.add_argument('json_path', help='JSON 文件路径')
    ip.add_argument('--db', default=r'D:\p\test-multiagent\data', help='目标数据库路径或目录')

    # migrate
    mp = subparsers.add_parser('migrate', help='数据库间迁移（含卡片/日志/审批）')
    mp.add_argument('--source', default=None, help='源数据库路径（默认项目 backend/data/multiagent.db）')
    mp.add_argument('--target', required=True, help='目标数据库路径或目录')
    mp.add_argument('--kanban-id', required=True, help='要迁移的看板 ID')

    args = parser.parse_args()

    if args.command == 'export':
        cmd_export(args)
    elif args.command == 'import':
        cmd_import(args)
    elif args.command == 'migrate':
        if not args.source:
            args.source = os.path.join(os.path.dirname(__file__), 'backend', 'data', 'multiagent.db')
        cmd_migrate(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
