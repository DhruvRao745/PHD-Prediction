from app.models.activity_log import ActivityLog


def log_activity(db, actor, action, description, target_type=None, target_id=None):
    """Writes one permanent activity_log row. `actor` is the same
    {id, role, username, email} dict every route already gets from
    get_current_user/get_current_admin - nothing extra to look up.

    Deliberately does NOT commit - callers already commit their own
    change (the assignment, the request, whatever) right after calling
    this, so the log entry lands in the exact same transaction as the
    action it's describing. That way the two can never drift apart (log
    written but action failed, or vice versa).
    """
    entry = ActivityLog(
        actor_id=actor["id"],
        actor_username=actor["username"],
        actor_role=actor["role"],
        action=action,
        description=description,
        target_type=target_type,
        target_id=target_id,
    )
    db.add(entry)
