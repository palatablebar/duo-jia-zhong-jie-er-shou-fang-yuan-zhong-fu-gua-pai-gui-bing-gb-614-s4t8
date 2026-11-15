"""ORM 模型聚合导出（Base 用于 create_all）。"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from src.models.user import User  # noqa: E402
from src.models.audit import AuditLog  # noqa: E402
from src.models.agency import Agency  # noqa: E402
from src.models.listing import Listing  # noqa: E402
from src.models.property import Property  # noqa: E402
from src.models.match_run import MatchRun  # noqa: E402
from src.models.review import Review  # noqa: E402

__all__ = ["Base", "User", "AuditLog", "Agency", "Listing", "Property", "MatchRun", "Review"]
