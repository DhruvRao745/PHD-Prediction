from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, CheckConstraint, Index
from datetime import datetime
from app.database import Base


class ActivityLog(Base):
    """Permanent record of who did what, when. Written once at the
    moment an action happens and never edited afterward - that's what
    makes it an audit trail instead of just another status field.

    actor_username/actor_role are stored as a snapshot (not just looked
    up live via actor_id) on purpose: if that account's username ever
    changes, or hypothetically gets removed later, this row still reads
    correctly exactly as it happened. Same reasoning behind denormalizing
    onto other audit-style rows elsewhere in this project.
    """

    __tablename__ = "activity_log"

    id = Column(Integer, primary_key=True, index=True)

    actor_id = Column(Integer, ForeignKey("accounts.id"), nullable=True, index=True)
    actor_username = Column(String, nullable=False)
    actor_role = Column(String, nullable=False)

    # Short machine-friendly code (e.g. "assign_patient") - lets the UI
    # filter/group without parsing free text.
    action = Column(String, nullable=False, index=True)

    # Human-readable, precomputed at write time - e.g. "Assigned Dr.
    # Mehta to R. Shah for heart disease". Precomputed (not rebuilt later
    # from IDs) so the log still reads correctly even if the underlying
    # names/records change or disappear afterward.
    description = Column(String, nullable=False)

    # What this action was about, so the log can link back to it if that
    # record still exists - both nullable since not every action has a
    # single obvious target (e.g. none needed for some future action types).
    target_type = Column(String, nullable=True)
    target_id = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        CheckConstraint("actor_role IN ('patient', 'doctor', 'admin')", name="ck_activity_log_actor_role"),
        Index("ix_activity_log_target", "target_type", "target_id"),
    )
