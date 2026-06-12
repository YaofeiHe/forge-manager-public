from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path
import unittest

from forge_manager.collectors.codex import collect_codex
from forge_manager.cli import _asks_for_activity, _asks_for_task_search, _project_filter_for_text, _query_for_text, _time_bounds_for_text
from forge_manager.config import Config, ProjectProfile
from forge_manager.db import Store
from forge_manager.reports.activity import activity_report
from forge_manager.reports.capabilities import capabilities_report
from forge_manager.reports.project import project_report


class ActivityAndCapabilitiesTests(unittest.TestCase):
    def test_collect_codex_records_user_message_and_assigns_project_by_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_path = root / "nexus"
            project_path.mkdir()
            codex_home = root / ".codex"
            codex_home.mkdir()
            rollout = codex_home / "rollout.jsonl"
            rollout.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "timestamp": "2026-06-09T01:00:00Z",
                                "type": "response_item",
                                "payload": {
                                    "type": "message",
                                    "role": "user",
                                    "content": [{"type": "input_text", "text": "[$nexus-workflow] 列表展示nexus项目活跃状态"}],
                                },
                            }
                        ),
                        json.dumps({"timestamp": "2026-06-09T01:01:00Z", "type": "event_msg", "payload": {"type": "task_started"}}),
                    ]
                )
            )
            self._write_codex_state(codex_home / "state_5.sqlite", rollout)
            store = Store(root / "store.sqlite")
            store.init()
            config = self._config(root, codex_home)

            collect_codex(config, store)

            with store.connect() as conn:
                item = conn.execute("select * from work_items where id='codex:thread-1'").fetchone()
                event = conn.execute("select * from events where event_type='user_message'").fetchone()

            self.assertIsNotNone(item)
            self.assertEqual(item["parent_id"], "nexus")
            self.assertEqual(item["status"], "running")
            self.assertIsNotNone(event)
            self.assertIn("nexus项目活跃状态", event["message"])

    def test_activity_report_filters_to_active_project_conversations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = Store(root / "store.sqlite")
            store.init()
            store.upsert_work_item("forge", "workspace", "forge", "running")
            store.upsert_work_item("nexus", "project", "nexus", "idle", parent_id="forge")
            store.upsert_work_item("codex:active", "run", "codex:active task", "running", parent_id="nexus", goal="active goal")
            store.upsert_work_item("codex:done", "run", "codex:done task", "idle", parent_id="nexus", goal="done goal")
            store.upsert_work_item("nexus:git", "branch", "git:main", "running", parent_id="nexus", goal="")
            store.add_event("codex:active", 1780970000, "codex", "user_message", "今天继续分析 nexus")
            store.add_event("codex:active", 1780970010, "codex", "thread_status", "running: latest task_started has no matching task_complete")
            store.add_event("codex:done", 1780970020, "codex", "user_message", "已经完成的 nexus 问题")
            store.add_event("nexus:git", 1780970030, "git", "git_status", "branch=main; dirty=True")
            store.add_link("codex:active", "codex_rollout", "/tmp/rollout-active.jsonl", "rollout JSONL")

            output = activity_report(store, 1780960000, 1780980000, project_id="nexus", active_only=True)

            self.assertIn("nexus", output)
            self.assertIn("  - 任务：active task [running]", output)
            self.assertIn("    - 源文件：/tmp/rollout-active.jsonl", output)
            self.assertIn("    - 内容：active goal", output)
            self.assertIn("    - 结果：仍在运行", output)
            self.assertNotIn("done task", output)
            self.assertNotIn("git:main", output)

    def test_activity_report_filters_by_query_and_summarizes_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = Store(root / "store.sqlite")
            store.init()
            store.upsert_work_item("forge", "workspace", "forge", "running")
            store.upsert_work_item("nexus", "project", "nexus", "idle", parent_id="forge")
            store.upsert_work_item("codex:restore", "run", "codex:恢复协议分析", "stale", parent_id="nexus", goal="分析 Nexus 恢复协议")
            store.upsert_work_item("codex:qwen", "run", "codex:qwen 配置", "running", parent_id="nexus", goal="配置 qwen 模型")
            store.add_event("codex:restore", 1780970000, "codex", "user_message", "总结 nexus 恢复协议任务")
            store.add_event("codex:restore", 1780970010, "codex", "thread_status", "stale: task_started without task_complete")
            store.add_event("codex:qwen", 1780970020, "codex", "user_message", "配置 qwen 模型")

            output = activity_report(
                store,
                1780960000,
                1780980000,
                project_id="nexus",
                active_only=True,
                query="恢复协议",
                statuses={"stale"},
                summarize=True,
            )

            self.assertIn("- 项目：nexus", output)
            self.assertIn("  - 任务：恢复协议分析 [stale]", output)
            self.assertIn("    - 内容：分析 Nexus 恢复协议", output)
            self.assertIn("    - 结果：未完成且长期无更新", output)
            self.assertNotIn("codex:qwen 配置", output)

    def test_activity_report_matches_assistant_results_across_projects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = Store(root / "store.sqlite")
            store.init()
            store.upsert_work_item("forge", "workspace", "forge", "running")
            store.upsert_work_item("codpm", "project", "codpm", "idle", parent_id="forge")
            store.upsert_work_item(
                "codex:codpm-sync",
                "run",
                "codex:补全初始化流程",
                "idle",
                parent_id="codpm",
                goal="检查 codpm 初始化产物",
            )
            store.add_event("codex:codpm-sync", 1780970000, "codex", "user_message", "检查 codpm 初始化")
            store.add_event(
                "codex:codpm-sync",
                1780970200,
                "codex",
                "assistant_message",
                "已完成 Nexus recovery-playbook 同步，并验证外部 Codex 修复后可回到原暂停点。",
            )

            output = activity_report(
                store,
                1780960000,
                1780980000,
                active_only=False,
                query="Nexus recovery-playbook 外部 Codex 暂停点",
            )

            self.assertIn("- 项目：codpm", output)
            self.assertIn("  - 任务：补全初始化流程 [idle]", output)
            self.assertIn("已完成 Nexus recovery-playbook 同步", output)

    def test_activity_report_prefers_task_complete_result_for_stale_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = Store(root / "store.sqlite")
            store.init()
            store.upsert_work_item("forge", "workspace", "forge", "running")
            store.upsert_work_item("nexus", "project", "nexus", "idle", parent_id="forge")
            store.upsert_work_item(
                "codex:restore",
                "run",
                "codex:外层 Codex 执行闭环",
                "stale",
                parent_id="nexus",
                goal="分析外层 Codex 执行闭环",
            )
            store.add_event("codex:restore", 1780970000, "codex", "user_message", "分析外层 Codex 执行闭环")
            store.add_event("codex:restore", 1780970010, "codex", "thread_status", "stale: task_started without task_complete")
            store.add_event(
                "codex:restore",
                1780970020,
                "codex",
                "task_complete",
                "产出外层执行协议硬化方向：进入 Nexus Workflow 后只执行 interaction.json 下一步。",
            )

            output = activity_report(store, 1780960000, 1780980000, project_id="nexus", active_only=True, query="interaction.json 下一步")

            self.assertIn("索引状态为 stale", output)
            self.assertIn("最新可见结果", output)
            self.assertIn("interaction.json 下一步", output)

    def test_activity_report_filters_internal_model_nodes_from_task_search(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = Store(root / "store.sqlite")
            store.init()
            store.upsert_work_item("forge", "workspace", "forge", "running")
            store.upsert_work_item("nexus", "project", "nexus", "idle", parent_id="forge")
            store.upsert_work_item(
                "codex:intent-node",
                "run",
                "codex:你是 nexus workflow kernel 的模型节点。 请严格返回符合 JSON Schema 的 JSON 对象",
                "idle",
                parent_id="nexus",
                goal="你是 nexus workflow kernel 的模型节点。 请严格返回符合 JSON Schema 的 JSON 对象。",
            )
            store.add_event(
                "codex:intent-node",
                1780970000,
                "codex",
                "assistant_message",
                '{"schema":"intent_route.v1","reason":"外部 Codex 修复 Nexus workflow 暂停点"}',
            )
            store.upsert_work_item(
                "codex:user-task",
                "run",
                "codex:外部 Codex 执行闭环分析",
                "idle",
                parent_id="nexus",
                goal="分析外部 Codex 修复后回到原 Nexus 暂停点",
            )
            store.add_event(
                "codex:user-task",
                1780970100,
                "codex",
                "assistant_message",
                "产出外部 Codex 执行闭环规划，覆盖回到原 Nexus 暂停点继续完整工作流。",
            )

            output = activity_report(
                store,
                1780960000,
                1780980000,
                active_only=False,
                query="外部 Codex 修复 Nexus 暂停点 完整工作流",
            )

            self.assertIn("外部 Codex 执行闭环分析", output)
            self.assertNotIn("intent-node", output)
            self.assertNotIn("JSON Schema", output)

    def test_activity_report_ignores_instruction_context_for_query_matching(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = Store(root / "store.sqlite")
            store.init()
            store.upsert_work_item("forge", "workspace", "forge", "running")
            store.upsert_work_item("codpm", "project", "codpm", "idle", parent_id="forge")
            store.upsert_work_item(
                "codex:rule-list",
                "run",
                "codex:列出所有规则",
                "idle",
                parent_id="codpm",
                goal="列出所有规则",
            )
            store.add_event(
                "codex:rule-list",
                1780970000,
                "codex",
                "user_message",
                "# AGENTS.md instructions\nNexus workflow 外部 Codex 修复 回到原暂停点\n\n## My request for Codex:\n列出所有规则",
            )
            store.add_event("codex:rule-list", 1780970100, "codex", "assistant_message", "已列出当前所有规则。")

            output = activity_report(
                store,
                1780960000,
                1780980000,
                active_only=False,
                query="Nexus workflow 外部 Codex 修复 暂停点",
            )

            self.assertIn("No matching conversations/tasks found", output)
            self.assertNotIn("列出所有规则 [idle]", output)

    def test_activity_report_markdown_includes_codex_deep_link_and_rollout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = Store(root / "store.sqlite")
            store.init()
            store.upsert_work_item("forge", "workspace", "forge", "running")
            store.upsert_work_item("nexus", "project", "nexus", "idle", parent_id="forge")
            store.upsert_work_item(
                "codex:thread-1",
                "run",
                "codex:查找 nexus 恢复任务",
                "running",
                parent_id="nexus",
                goal="查找外部 Codex 修复后回到原 Nexus 暂停点的任务",
            )
            store.add_event("codex:thread-1", 1780970000, "codex", "user_message", "查找 nexus 恢复任务")
            store.add_event("codex:thread-1", 1780970010, "codex", "thread_status", "running: latest task_started has no matching task_complete")
            store.add_link("codex:thread-1", "codex_thread", "thread-1", "Codex thread")
            store.add_link("codex:thread-1", "codex_rollout", "/tmp/rollout-thread-1.jsonl", "rollout JSONL")

            output = activity_report(store, 1780960000, 1780980000, view="markdown", project_id="nexus", active_only=True)

            self.assertIn("- 项目：nexus", output)
            self.assertIn("  - 任务：查找 nexus 恢复任务 [running]", output)
            self.assertIn("    - 深度链接：codex://threads/thread-1", output)
            self.assertIn("    - 源文件：/tmp/rollout-thread-1.jsonl", output)
            self.assertIn("    - 内容：查找外部 Codex 修复后回到原 Nexus 暂停点的任务", output)

    def test_activity_report_markdown_does_not_fabricate_missing_thread_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = Store(root / "store.sqlite")
            store.init()
            store.upsert_work_item("forge", "workspace", "forge", "running")
            store.upsert_work_item("nexus", "project", "nexus", "idle", parent_id="forge")
            store.upsert_work_item("codex:no-thread", "run", "codex:无深链任务", "running", parent_id="nexus", goal="没有 thread link")
            store.add_event("codex:no-thread", 1780970000, "codex", "user_message", "没有 thread link")

            output = activity_report(store, 1780960000, 1780980000, view="markdown", project_id="nexus", active_only=True)

            self.assertIn("  - 任务：无深链任务 [running]", output)
            self.assertIn("    - 深度链接：未记录", output)
            self.assertIn("    - 源文件：未记录", output)
            self.assertNotIn("codex://threads/", output)

    def test_project_report_formats_codex_thread_links_as_deep_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = Store(root / "store.sqlite")
            store.init()
            store.upsert_work_item("forge", "workspace", "forge", "running")
            store.upsert_work_item("nexus", "project", "nexus", "idle", parent_id="forge")
            store.upsert_work_item("codex:thread-1", "run", "codex:linked task", "running", parent_id="nexus", goal="linked")
            store.add_link("codex:thread-1", "codex_thread", "thread-1", "Codex thread")

            output = project_report(store, "nexus")

            self.assertIn("- codex_thread: [thread-1](codex://threads/thread-1) (Codex thread)", output)

    def test_natural_language_task_defaults_and_rolling_time(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            codex_home = root / ".codex"
            codex_home.mkdir()
            config = self._config(root, codex_home)

            self.assertTrue(_asks_for_activity("列表展示项目状态"))
            self.assertTrue(_asks_for_activity("查看 nexus 任务", project_id="nexus"))
            self.assertTrue(_asks_for_task_search("找到24小时内和恢复有关的任务"))
            self.assertEqual(_query_for_text(config, "查找24小时内 nexus stale 任务：恢复"), "恢复")
            self.assertEqual(_query_for_text(config, "总结 nexus 中关于恢复协议的任务"), "恢复协议")
            self.assertEqual(_query_for_text(config, "查找24小时内 nexus 恢复 任务，按照markdown格式展示并加深度链接"), "nexus 恢复")
            self.assertIsNone(_project_filter_for_text(config, "查找48小时内所有项目和 nexus 工作流恢复有关的任务", strict=True))
            self.assertIsNone(_project_filter_for_text(config, "查找48小时内和 nexus 工作流恢复有关的任务", strict=True))
            self.assertEqual(_project_filter_for_text(config, "查找48小时内 nexus 项目内恢复任务", strict=True), "nexus")
            self.assertEqual(_query_for_text(config, "查找48小时内 nexus 项目内恢复任务", project_id="nexus"), "恢复")
            self.assertEqual(_query_for_text(config, "找到24小时内和“外部 Codex 修复”有关的任务，并且按照项目-任务结构组织一个列表"), "外部 Codex 修复")
            start, end = _time_bounds_for_text("列表展示24小时内项目状态")
            self.assertGreaterEqual(end - start, 23 * 60 * 60)
            self.assertLessEqual(end - start, 24 * 60 * 60 + 2)

    def test_capabilities_report_uses_project_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            codex_home = root / ".codex"
            codex_home.mkdir()
            store = Store(root / "store.sqlite")
            store.init()
            store.upsert_work_item("forge", "workspace", "forge", "running")
            store.upsert_work_item("nexus", "project", "nexus", "idle", parent_id="forge")
            config = self._config(root, codex_home)

            output = capabilities_report(config, store)

            self.assertIn("forge children", output)
            self.assertIn("nexus [idle]: 项目调研、意图路由", output)

    def _config(self, root: Path, codex_home: Path) -> Config:
        project_path = root / "nexus"
        project_path.mkdir(exist_ok=True)
        profile = ProjectProfile(
            project_id="nexus",
            path=project_path,
            capability="项目调研、意图路由、规划生成",
            aliases=("nexus-workflow", "$nexus-workflow"),
        )
        return Config(
            root=root,
            codex_home=codex_home,
            data_dir=root,
            db_path=root / "store.sqlite",
            projects={"nexus": project_path},
            project_profiles={"nexus": profile},
        )

    def _write_codex_state(self, db_path: Path, rollout: Path) -> None:
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                """
                create table threads (
                  id text,
                  title text,
                  first_user_message text,
                  cwd text,
                  rollout_path text,
                  created_at integer,
                  updated_at integer,
                  archived integer
                )
                """
            )
            conn.execute(
                "insert into threads values (?, ?, ?, ?, ?, ?, ?, ?)",
                ("thread-1", "", "", "", str(rollout), 1780966800, 1780966860, 0),
            )
            conn.commit()
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
