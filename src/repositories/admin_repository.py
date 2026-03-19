from sqlalchemy import select

from src.models.entities import AppRegistry


class AdminRepository:
    def __init__(self, session):
        self.session = session

    def list_apps(self):
        stmt = select(AppRegistry).where(AppRegistry.is_enabled.is_(True)).order_by(AppRegistry.display_order)
        return self.session.scalars(stmt).all()
