"""応答率エンジン用マスタ（除外番号・放棄閾値・合算定義・OP）の管理サービス。

削除は行わず is_active=false（Operatorは status）で無効化するのを基本とする。
"""
from src.models.entities import AbandonRule, ExcludeNumber, Operator, SkillGroupMerge

# 業務グループ候補の初期キーワード（DB保存しない。画面で追加・編集可能）。
# skill_group 名にこのキーワードを含む回線を1つの候補グループとしてまとめる。
DEFAULT_GROUP_CANDIDATE_KEYWORDS = (
    "ネオマルス",
    "弁護士ドットコム",
    "ヨシケイ",
    "KDDI",
    "LEOC",
    "RPA",
)

# 大きい候補を地域名で分割するための初期キーワード（DB保存しない。画面で編集可能）。
DEFAULT_REGION_KEYWORDS = (
    "東京",
    "横浜",
    "大阪",
    "名古屋",
    "札幌",
    "仙台",
    "千葉",
    "埼玉",
    "神戸",
    "京都",
    "福岡",
    "広島",
)


class AnswerRateMasterService:
    def __init__(self, answer_rate_master_repository, audit_service=None):
        self.repo = answer_rate_master_repository
        self.audit_service = audit_service

    def _audit(self, table, record_id, action, actor_id, after=None):
        if self.audit_service:
            self.audit_service.log(table, record_id, action, actor_id, after=after)

    # --- exclude_numbers ---
    def list_exclude_numbers(self):
        return [
            {"id": x.id, "caller_number": x.caller_number, "reason": x.reason or "", "is_active": x.is_active}
            for x in self.repo.list_exclude_numbers(active_only=False)
        ]

    def create_exclude_number(self, actor_id: int, caller_number: str, reason: str):
        obj = ExcludeNumber(caller_number=caller_number.strip(), reason=reason.strip() or None, is_active=True)
        self.repo.add(obj)
        self._audit("exclude_numbers", obj.id, "create", actor_id, after=obj)
        return obj

    def toggle_exclude_number(self, actor_id: int, id_: int):
        obj = self.repo.get_exclude_number(id_)
        if obj:
            obj.is_active = not obj.is_active
            self.repo.add(obj)
            self._audit("exclude_numbers", obj.id, "update", actor_id, after=obj)
        return obj

    # --- abandon_rules ---
    def list_abandon_rules(self):
        return [
            {
                "id": r.id,
                "skill_group": r.skill_group or "(全体既定)",
                "threshold_seconds": r.threshold_seconds,
                "is_active": r.is_active,
            }
            for r in self.repo.list_abandon_rules(active_only=False)
        ]

    def create_abandon_rule(self, actor_id: int, skill_group: str | None, threshold_seconds: int):
        sg = (skill_group or "").strip() or None
        obj = AbandonRule(skill_group=sg, threshold_seconds=int(threshold_seconds), is_active=True)
        self.repo.add(obj)
        self._audit("abandon_rules", obj.id, "create", actor_id, after=obj)
        return obj

    def update_abandon_rule(self, actor_id: int, id_: int, threshold_seconds: int):
        obj = self.repo.get_abandon_rule(id_)
        if obj:
            obj.threshold_seconds = int(threshold_seconds)
            self.repo.add(obj)
            self._audit("abandon_rules", obj.id, "update", actor_id, after=obj)
        return obj

    def toggle_abandon_rule(self, actor_id: int, id_: int):
        obj = self.repo.get_abandon_rule(id_)
        if obj:
            obj.is_active = not obj.is_active
            self.repo.add(obj)
            self._audit("abandon_rules", obj.id, "update", actor_id, after=obj)
        return obj

    # --- skill_group_merge ---
    def list_skill_group_merge(self):
        return [
            {
                "id": m.id,
                "merge_label": m.merge_label,
                "child_skill_group": m.child_skill_group,
                "is_active": m.is_active,
            }
            for m in self.repo.list_skill_group_merge(active_only=False)
        ]

    def create_skill_group_merge(self, actor_id: int, merge_label: str, child_skill_group: str):
        obj = SkillGroupMerge(
            merge_label=merge_label.strip(),
            child_skill_group=child_skill_group.strip(),
            is_active=True,
        )
        self.repo.add(obj)
        self._audit("skill_group_merge", obj.id, "create", actor_id, after=obj)
        return obj

    def create_skill_group_merge_bulk(self, actor_id: int, merge_label: str, child_skill_groups) -> dict:
        """1つの業務グループ(merge_label)へ複数の子スキルグループを一括登録する。

        既存と重複する (merge_label, child) はスキップする。
        戻り値は {added, skipped, label}（UI層へORMは渡さない）。
        """
        label = (merge_label or "").strip()
        if not label:
            raise ValueError("業務グループ名（親ラベル）を入力してください。")
        children = sorted({str(c).strip() for c in child_skill_groups if str(c).strip()})
        if not children:
            raise ValueError("子スキルグループを1件以上選択してください。")

        existing_pairs = {
            (m.merge_label, m.child_skill_group)
            for m in self.repo.list_skill_group_merge(active_only=False)
        }
        added, skipped = 0, 0
        for child in children:
            if (label, child) in existing_pairs:
                skipped += 1
                continue
            obj = SkillGroupMerge(merge_label=label, child_skill_group=child, is_active=True)
            self.repo.add(obj)
            self._audit("skill_group_merge", obj.id, "create", actor_id, after=obj)
            added += 1
        return {"added": added, "skipped": skipped, "label": label}

    def build_group_candidates(self, skill_groups, keywords=None) -> list[dict]:
        """取込済み skill_group 一覧から、キーワードを含む回線を業務グループ候補としてまとめる。

        自動登録はしない（候補を返すだけ）。UI層へORMは渡さず list[dict] を返す。
        各候補: {label, keyword, lines, line_count, registered_count,
                 unregistered_count, fully_registered}
        - label の初期値はキーワード（UIで編集可能）。
        - registered_count は「キーワードと同名の merge_label」に既に登録済みの回線数。
        """
        kw_list = keywords if keywords is not None else list(DEFAULT_GROUP_CANDIDATE_KEYWORDS)
        # 重複・空白を除去しつつ入力順を維持
        seen = set()
        norm_keywords = []
        for kw in kw_list:
            k = str(kw).strip()
            if k and k.lower() not in seen:
                seen.add(k.lower())
                norm_keywords.append(k)

        groups = [str(sg) for sg in skill_groups]
        existing_pairs = {
            (m.merge_label, m.child_skill_group)
            for m in self.repo.list_skill_group_merge(active_only=False)
        }

        candidates = []
        for kw in norm_keywords:
            matched = sorted({sg for sg in groups if kw.lower() in sg.lower()})
            if not matched:
                continue
            registered = [sg for sg in matched if (kw, sg) in existing_pairs]
            candidates.append(
                {
                    "label": kw,
                    "keyword": kw,
                    "lines": matched,
                    "line_count": len(matched),
                    "registered_count": len(registered),
                    "unregistered_count": len(matched) - len(registered),
                    "fully_registered": len(registered) == len(matched),
                }
            )
        return candidates

    def build_split_group_candidates(self, parent_candidate: dict, region_keywords=None) -> list[dict]:
        """大きい業務グループ候補を地域名で分割した子候補を返す（自動登録はしない）。

        分割ルール（現実的・優先順）:
          1. skill_group 名に含まれる地域名（region_keywords）で振り分ける。
             複数地域が含まれる場合は region_keywords の並び順で最初に一致した地域へ入れる。
          2. どの地域名にも当たらない回線は「(親名)_未分類」候補へまとめる。

        完全自動分類は危険なため、あくまで候補（list[dict]）を返すだけ。UI層へORMは渡さない。
        各子候補: {label, keyword(親), region, lines, line_count,
                   registered_count, unregistered_count, fully_registered}
        """
        regions_src = region_keywords if region_keywords is not None else list(DEFAULT_REGION_KEYWORDS)
        seen = set()
        regions = []
        for r in regions_src:
            rr = str(r).strip()
            if rr and rr not in seen:
                seen.add(rr)
                regions.append(rr)

        parent_label = str(parent_candidate.get("label") or parent_candidate.get("keyword") or "").strip()
        keyword = parent_candidate.get("keyword", parent_label)
        lines = [str(x) for x in (parent_candidate.get("lines") or [])]

        existing_pairs = {
            (m.merge_label, m.child_skill_group)
            for m in self.repo.list_skill_group_merge(active_only=False)
        }

        buckets: dict[str, list[str]] = {r: [] for r in regions}
        unclassified: list[str] = []
        for line in lines:
            matched_region = next((r for r in regions if r in line), None)
            if matched_region is not None:
                buckets[matched_region].append(line)
            else:
                unclassified.append(line)

        def _candidate(label: str, region: str, group_lines: list[str]) -> dict:
            group_lines = sorted(group_lines)
            registered = [sg for sg in group_lines if (label, sg) in existing_pairs]
            return {
                "label": label,
                "keyword": keyword,
                "region": region,
                "lines": group_lines,
                "line_count": len(group_lines),
                "registered_count": len(registered),
                "unregistered_count": len(group_lines) - len(registered),
                "fully_registered": bool(group_lines) and len(registered) == len(group_lines),
            }

        result = []
        for r in regions:
            if buckets[r]:
                result.append(_candidate(f"{parent_label}_{r}", r, buckets[r]))
        if unclassified:
            result.append(_candidate(f"{parent_label}_未分類", "未分類", unclassified))
        return result

    def toggle_skill_group_merge(self, actor_id: int, id_: int):
        obj = self.repo.get_skill_group_merge(id_)
        if obj:
            obj.is_active = not obj.is_active
            self.repo.add(obj)
            self._audit("skill_group_merge", obj.id, "update", actor_id, after=obj)
        return obj

    # --- operators ---
    def list_operators(self):
        return [
            {
                "id": o.id,
                "op_code": o.op_code,
                "display_name": o.display_name,
                "skill_group": o.skill_group or "",
                "status": o.status,
                "shift_type": o.shift_type or "",
            }
            for o in self.repo.list_operators(active_only=False)
        ]

    def create_operator(self, actor_id: int, op_code: str, display_name: str, skill_group: str, shift_type: str):
        if self.repo.get_operator_by_code(op_code.strip()):
            raise ValueError("同じ op_code のオペレーターが既に存在します。")
        obj = Operator(
            op_code=op_code.strip(),
            display_name=display_name.strip(),
            skill_group=(skill_group or "").strip() or None,
            status="active",
            shift_type=(shift_type or "").strip() or None,
        )
        self.repo.add(obj)
        self._audit("operators", obj.id, "create", actor_id, after=obj)
        return obj

    def toggle_operator(self, actor_id: int, id_: int):
        obj = self.repo.get_operator(id_)
        if obj:
            obj.status = "inactive" if obj.status == "active" else "active"
            self.repo.add(obj)
            self._audit("operators", obj.id, "update", actor_id, after=obj)
        return obj
