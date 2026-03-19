from decimal import Decimal, ROUND_HALF_UP

from src.models.entities import LeocSnapshot


class LeocService:
    def __init__(self, leoc_repository, audit_service):
        self.leoc_repository = leoc_repository
        self.audit_service = audit_service

    def aggregate_counts(self, creators: list[str], lost_count: int):
        ai_count = sum(1 for x in creators if "mpg1" in x.lower())
        form_count = sum(1 for x in creators if "takeyama" in x.lower())
        inbound_count = len(creators) - ai_count - form_count
        denominator = inbound_count + lost_count
        if denominator == 0:
            answer_rate = Decimal("0.0")
        else:
            rate = Decimal(inbound_count * 100) / Decimal(denominator)
            answer_rate = rate.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        return {
            "inbound_count": inbound_count,
            "lost_count": lost_count,
            "answer_rate": float(answer_rate),
            "ai_count": ai_count,
            "form_count": form_count,
        }

    def build_post_text(self, snapshot_time: str, inbound_count: int, lost_count: int, answer_rate: float, ai_count: int, form_count: int):
        denominator = inbound_count + lost_count
        return (
            f"{snapshot_time}時点 OK\n"
            f"入電：{inbound_count}/{denominator} {answer_rate:.1f}%\n"
            f"AI：{ai_count}\n"
            f"Form：{form_count}"
        )

    def create_snapshot(self, actor_id: int, snapshot_time: str, lost_count: int, creators: list[str]):
        counts = self.aggregate_counts(creators, lost_count)
        post_text = self.build_post_text(snapshot_time, **counts)
        snapshot = LeocSnapshot(
            snapshot_time=snapshot_time,
            inbound_count=counts["inbound_count"],
            lost_count=counts["lost_count"],
            answer_rate=counts["answer_rate"],
            ai_count=counts["ai_count"],
            form_count=counts["form_count"],
            source_type="manual",
            source_ref="\n".join(creators),
            created_by=actor_id,
        )
        self.leoc_repository.create_snapshot(snapshot)
        self.audit_service.log("leoc_snapshots", snapshot.snapshot_id, "create", actor_id, after=snapshot)
        return counts | {"post_text": post_text, "snapshot_time": snapshot_time}

    def list_history_for_display(self):
        rows = []
        for x in self.leoc_repository.list_history():
            rows.append(
                {
                    "created_at": x.created_at,
                    "snapshot_time": x.snapshot_time,
                    "inbound_count": x.inbound_count,
                    "lost_count": x.lost_count,
                    "answer_rate": float(x.answer_rate),
                    "ai_count": x.ai_count,
                    "form_count": x.form_count,
                    "post_text": self.build_post_text(
                        x.snapshot_time,
                        x.inbound_count,
                        x.lost_count,
                        float(x.answer_rate),
                        x.ai_count,
                        x.form_count,
                    ),
                }
            )
        return rows

    def latest_for_dashboard(self):
        latest = self.leoc_repository.latest()
        if not latest:
            return None
        return {
            "answer_rate": f'{float(latest.answer_rate):.1f}%',
            "post_text": self.build_post_text(
                latest.snapshot_time,
                latest.inbound_count,
                latest.lost_count,
                float(latest.answer_rate),
                latest.ai_count,
                latest.form_count,
            ),
        }
