"""通話呼詳細CSV（CDR）取込サービス。

方針:
- 生CSVは非破壊。元ファイルを編集しない（アップロード内容はメモリ上で扱う）。
- エンコード読込順: utf-8-sig → cp932 → charset-normalizer 自動判定。
- 失敗ファイルは uploads/quarantine/ に退避し、import_log に status=failed を残す。
- commit 前に必ずプレビュー（集計結果・件数・衝突）を返す。保存はユーザー確認後。
- call_stats には raw skill_group の集計値のみ保存。合算は保存しない。
- import_log に engine_version / threshold_rule_snapshot_json /
  exclude_numbers_snapshot_hash / definition_note を必ず保存する。
"""
import io
import os
from datetime import datetime

import pandas as pd

from src.models.entities import ImportLog
from src.services import answer_rate_service as ar


class CdrImportError(Exception):
    pass


class CdrImportService:
    ENCODINGS_TRY = ["utf-8-sig", "cp932"]

    def __init__(self, call_stats_repository, answer_rate_master_repository, audit_service=None,
                 quarantine_dir: str = "uploads/quarantine"):
        self.call_stats_repository = call_stats_repository
        self.master_repository = answer_rate_master_repository
        self.audit_service = audit_service
        self.quarantine_dir = quarantine_dir

    # ------------------------------------------------------------------
    # 読込
    # ------------------------------------------------------------------
    def detect_and_read(self, raw: bytes) -> tuple[str, pd.DataFrame]:
        """エンコードを順に試し、(encoding, DataFrame) を返す。全て失敗で CdrImportError。"""
        last_error = None
        for enc in self.ENCODINGS_TRY:
            try:
                df = pd.read_csv(io.BytesIO(raw), encoding=enc, dtype=str, low_memory=False)
                return enc, df
            except Exception as exc:  # noqa: BLE001 - 次の候補へフォールバック
                last_error = exc
        # 自動判定（charset-normalizer）
        try:
            from charset_normalizer import from_bytes

            best = from_bytes(raw).best()
            if best is not None and best.encoding:
                enc = best.encoding
                df = pd.read_csv(io.BytesIO(raw), encoding=enc, dtype=str, low_memory=False)
                return enc, df
        except Exception as exc:  # noqa: BLE001
            last_error = exc
        raise CdrImportError(f"CSVのエンコード判定・読込に失敗しました: {last_error}")

    # ------------------------------------------------------------------
    # スナップショット（取込時点のルールを後から再現可能にする）
    # ------------------------------------------------------------------
    def build_snapshots(self) -> dict:
        abandon_rules = self.master_repository.list_abandon_rules(active_only=True)
        exclude_numbers = self.master_repository.list_exclude_numbers(active_only=True)
        threshold_rules = ar.build_threshold_rules(abandon_rules)
        exclude_set, exclude_hash = ar.exclude_set_and_hash(exclude_numbers)
        return {
            "threshold_rules": threshold_rules,
            "exclude_set": exclude_set,
            "exclude_hash": exclude_hash,
        }

    # ------------------------------------------------------------------
    # プレビュー（DB書込みなし）
    # ------------------------------------------------------------------
    def prepare(self, raw: bytes, filename: str, mapping: dict) -> dict:
        """読込→検証→集計→衝突チェックまで。DBには書き込まない。

        失敗時は quarantine + import_log(failed) を行い CdrImportError を送出する。
        """
        try:
            encoding, df = self.detect_and_read(raw)
        except CdrImportError as exc:
            self._quarantine_and_log_failed(raw, filename, encoding=None, row_count=None, error=str(exc))
            raise

        missing = ar.validate_mapping(df.columns, mapping)
        if missing:
            actual = [mapping[k] for k in missing]
            msg = f"必須列が見つかりません: {', '.join(actual)}（論理項目: {', '.join(missing)}）"
            self._quarantine_and_log_failed(raw, filename, encoding=encoding, row_count=len(df), error=msg)
            raise CdrImportError(msg)

        snapshots = self.build_snapshots()
        try:
            result = ar.aggregate(df, mapping, snapshots["threshold_rules"], snapshots["exclude_set"])
        except Exception as exc:  # noqa: BLE001
            msg = f"集計中にエラーが発生しました: {exc}"
            self._quarantine_and_log_failed(raw, filename, encoding=encoding, row_count=len(df), error=msg)
            raise CdrImportError(msg) from exc

        stats = result["stats"]
        keys = [(s["stat_date"], s["time_slot"], s["skill_group"]) for s in stats]
        collisions = self.call_stats_repository.exists_for_keys(keys)

        return {
            "filename": filename,
            "encoding": encoding,
            "row_count": len(df),
            "stats": stats,
            "summary": result["summary"],
            "collisions": collisions,
            "threshold_rule_snapshot_json": snapshots["threshold_rules"],
            "exclude_numbers_snapshot_hash": snapshots["exclude_hash"],
            "definition_note": ar.ELAPSED_APPROX_NOTE,
            "engine_version": ar.ENGINE_VERSION,
        }

    # ------------------------------------------------------------------
    # 確定保存（ユーザー確認後）
    # ------------------------------------------------------------------
    def commit(self, prepared: dict, actor_id: int, raw: bytes | None = None) -> dict:
        """プレビュー結果を call_stats へ保存し、import_log(completed) を残す。

        二重取込（ユニーク制約衝突）が残っている場合は保存せず failed を記録する。
        """
        if prepared.get("collisions"):
            msg = "同一期間・同一スキルグループのデータが既に取込済みです（二重取込）。"
            if raw is not None:
                self._quarantine_and_log_failed(
                    raw, prepared["filename"], encoding=prepared.get("encoding"),
                    row_count=prepared.get("row_count"), error=msg,
                )
            else:
                self._log_failed(prepared["filename"], prepared.get("encoding"),
                                 prepared.get("row_count"), msg)
            raise CdrImportError(msg)

        inserted = self.call_stats_repository.bulk_insert_stats(prepared["stats"])
        log = ImportLog(
            filename=prepared["filename"],
            encoding=prepared["encoding"],
            row_count=prepared["row_count"],
            status="completed",
            imported_at=datetime.utcnow(),
            engine_version=prepared["engine_version"],
            threshold_rule_snapshot_json=prepared["threshold_rule_snapshot_json"],
            exclude_numbers_snapshot_hash=prepared["exclude_numbers_snapshot_hash"],
            definition_note=prepared["definition_note"],
            error_message=None,
        )
        self.call_stats_repository.create_import_log(log)
        if self.audit_service:
            self.audit_service.log("import_log", log.id, "create", actor_id, after=log)
        return {"inserted_stat_rows": inserted, "import_log_id": log.id}

    # ------------------------------------------------------------------
    # 取込済み集計の削除（再取込用）
    # ------------------------------------------------------------------
    def delete_call_stats_range(self, start, end, actor_id: int, note: str | None = None) -> dict:
        """[start, end]（両端含む）の call_stats を削除し、操作を import_log に残す。

        用途: abandon_rules の秒数閾値を変更した後、既存の集計（0秒既定など）を削除し、
        同じCSVを再取込できるようにする。
        - 削除対象は raw skill_group の call_stats のみ（合算値は元々非保存のため対象外）。
        - DBスキーマは変更しない。call_stats と import_log を結ぶFKは無いため、
          削除は import_log 単位ではなく stat_date 範囲で行う（呼び出し側で範囲を指定する）。
        - 操作監査として import_log に status="deleted" の行を1件残す（スキーマ変更不要）。
        """
        deleted = self.call_stats_repository.delete_stats_in_range(start, end)
        log = ImportLog(
            filename=f"[call_stats削除] {start}〜{end}",
            encoding=None,
            row_count=deleted,
            status="deleted",
            imported_at=datetime.utcnow(),
            engine_version=ar.ENGINE_VERSION,
            threshold_rule_snapshot_json=None,
            exclude_numbers_snapshot_hash=None,
            definition_note=(
                note
                or f"再取込のため call_stats {deleted}行を削除（{start}〜{end} / raw skill_groupのみ・合算値は非保存）。"
            ),
            error_message=None,
        )
        self.call_stats_repository.create_import_log(log)
        if self.audit_service:
            self.audit_service.log("import_log", log.id, "delete_call_stats", actor_id, after=log)
        return {"deleted_rows": deleted, "import_log_id": log.id}

    # ------------------------------------------------------------------
    # 失敗時の退避・記録
    # ------------------------------------------------------------------
    def _quarantine(self, raw: bytes, filename: str) -> str:
        os.makedirs(self.quarantine_dir, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = os.path.basename(filename)
        dest = os.path.join(self.quarantine_dir, f"{stamp}__{safe_name}")
        with open(dest, "wb") as f:  # 生バイトをそのまま退避（非破壊・PowerShell不使用）
            f.write(raw)
        return dest

    def _log_failed(self, filename, encoding, row_count, error):
        log = ImportLog(
            filename=filename,
            encoding=encoding,
            row_count=row_count,
            status="failed",
            imported_at=datetime.utcnow(),
            engine_version=ar.ENGINE_VERSION,
            threshold_rule_snapshot_json=None,
            exclude_numbers_snapshot_hash=None,
            definition_note=ar.ELAPSED_APPROX_NOTE,
            error_message=str(error),
        )
        self.call_stats_repository.create_import_log(log)
        return log

    def _quarantine_and_log_failed(self, raw, filename, encoding, row_count, error):
        try:
            path = self._quarantine(raw, filename)
            error = f"{error} / 退避先: {path}"
        except Exception as exc:  # noqa: BLE001 - 退避失敗でもログは残す
            error = f"{error} / 退避失敗: {exc}"
        return self._log_failed(filename, encoding, row_count, error)
