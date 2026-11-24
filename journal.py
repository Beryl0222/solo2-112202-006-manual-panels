"""回查日志：把编校、拼装、机台判定留下的事件追加写成 JSONL。

每条事件带序号，内容确定（不含时间戳），方便测试与 diff。项目进入下一轮译
文或来了新机台时，按 kind / lang / hardware / screen 回查曾经遇到的字形、
短句歧义和安装范围。
"""
from __future__ import annotations

import json
from pathlib import Path


class Journal:
    def __init__(self):
        self.events = []

    def record(self, kind: str, **fields):
        self.events.append({"seq": len(self.events) + 1, "kind": kind, **fields})

    def query(self, **filters) -> list:
        def match(event):
            return all(event.get(key) == value for key, value in filters.items())

        return [event for event in self.events if match(event)]

    def write(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as sink:
            for event in self.events:
                sink.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")

    @staticmethod
    def read(path: Path) -> list:
        with Path(path).open(encoding="utf-8") as source:
            return [json.loads(line) for line in source if line.strip()]
