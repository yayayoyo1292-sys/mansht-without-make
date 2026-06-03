from __future__ import annotations

import time
import psycopg2

from config.settings import ENABLE_FACEBOOK_POSTING
from services.queue_manager import QueueManager
from services.publish_pipeline import PublishPipeline
from DB.db import db_execute
from utils.logger import logger

_queue    = QueueManager()
_pipeline = PublishPipeline()

# ─── Statuses that mean "done, never retry" ──────────────────────────────────
_FINAL_SKIP = frozenset({
    "skipped:high_priority_policy",
    "skipped:normal_priority_policy",
    "skipped:already_published",
    "skipped:fb_disabled",
    "skipped:fb_outside_date_window",
    "skipped:unknown_platform",
    "sent",
})

def _is_done(status: str) -> bool:
    return status in _FINAL_SKIP

def _needs_retry(status: str) -> bool:
    """Rate-limited or failed → must retry later."""
    return status.startswith("rate_limited") or status == "failed"


def _publish_one(post: dict) -> None:
    post_id    = post["id"]
    priority   = int(post.get("priority_score") or 0)
    title_snip = (post.get("title") or "")[:60]
    is_high    = priority >= 9  # mirrors PRIORITY_THRESHOLD_INSTAGRAM

    # ── Determine which platforms this post should go to ─────────────────────
    if is_high:
        target_platforms = {"instagram"}
    else:
        target_platforms = {"facebook", "twitter"}
    # Telegram always
    target_platforms.add("telegram")

    # ── Check which platforms are already done ────────────────────────────────
    current = {
        "telegram":  post.get("telegram_status")  or "pending",
        "instagram": post.get("instagram_status") or "pending",
        "facebook":  post.get("facebook_status")  or "pending",
        "twitter":   post.get("twitter_status")   or "pending",
    }

    # Platforms in target that still need work
    pending_platforms = [
        p for p in target_platforms
        if not _is_done(current[p])
    ]

    if not pending_platforms:
        # Everything done — mark published and exit
        db_execute(
            """
            UPDATE news_queue
            SET status = 'published', published_at = NOW(), last_updated = NOW()
            WHERE id = %s AND status = 'processing'
            """,
            (post_id,),
        )
        logger.debug(f"✅ All platforms done (worker skip) | id={post_id}")
        return

    # ── Publish pending platforms ─────────────────────────────────────────────
    results = _pipeline.publish(post, priority_score=priority)

    # Merge results with current state
    new_statuses = {}
    for p in ("telegram", "instagram", "facebook", "twitter"):
        if p in results:
            new_statuses[p] = results[p]
        else:
            # Not attempted this round — keep existing or mark skipped
            if _is_done(current[p]):
                new_statuses[p] = current[p]
            elif p not in target_platforms:
                # Platform not targeted for this priority level
                if is_high:
                    new_statuses[p] = "skipped:high_priority_policy"
                else:
                    new_statuses[p] = "skipped:normal_priority_policy"
            else:
                new_statuses[p] = current[p]

    # ── Decide final queue status ─────────────────────────────────────────────
    # Any targeted platform still needs retry?
    needs_retry = any(
        _needs_retry(new_statuses[p])
        for p in target_platforms
    )

    if needs_retry:
        # Put back to pending so the worker picks it up again after cooldown
        retry_delay_seconds = _get_retry_delay(new_statuses, target_platforms)

        db_execute(
            """
            UPDATE news_queue
            SET
                status           = 'pending',
                telegram_status  = %s,
                instagram_status = %s,
                facebook_status  = %s,
                twitter_status   = %s,
                retry_after      = NOW() + (%s || ' seconds')::interval,
                last_updated     = NOW()
            WHERE id = %s AND status = 'processing'
            """,
            (
                new_statuses["telegram"],
                new_statuses["instagram"],
                new_statuses["facebook"],
                new_statuses["twitter"],
                retry_delay_seconds,
                post_id,
            ),
        )
        logger.info(
            f"♻️  Retry queued | id={post_id} | retry in {retry_delay_seconds}s | "
            + " ".join(f"{p}={new_statuses[p]}" for p in target_platforms)
        )
    else:
        # All targeted platforms done
        db_execute(
            """
            UPDATE news_queue
            SET
                status           = 'published',
                telegram_status  = %s,
                instagram_status = %s,
                facebook_status  = %s,
                twitter_status   = %s,
                published_at     = NOW(),
                last_updated     = NOW()
            WHERE id = %s AND status = 'processing'
            """,
            (
                new_statuses["telegram"],
                new_statuses["instagram"],
                new_statuses["facebook"],
                new_statuses["twitter"],
                post_id,
            ),
        )
        logger.info(
            f"✅ Worker published | id={post_id} "
            f"tg={new_statuses['telegram']} "
            f"ig={new_statuses['instagram']} "
            f"tw={new_statuses['twitter']} "
            f"fb={new_statuses['facebook']}"
        )


def _get_retry_delay(statuses: dict, target_platforms: set) -> int:
    """
    استخرج أقل وقت انتظار من الـ rate_limited statuses.
    مثال: 'rate_limited:cooldown 73s remaining' → 75 (مع buffer 2 ثانية)
    """
    import re
    min_delay = 60  # default

    for p in target_platforms:
        s = statuses.get(p, "")
        if s.startswith("rate_limited"):
            m = re.search(r"(\d+)s", s)
            if m:
                secs = int(m.group(1)) + 2  # buffer صغير
                min_delay = min(min_delay, secs)

    return max(min_delay, 10)  # على الأقل 10 ثواني


def publishing_worker() -> None:
    logger.info("🚀 Publishing worker started")
    consecutive_errors = 0

    while True:
        try:
            recovered = _queue.fail_stale_processing(max_minutes=10)
            if recovered:
                logger.warning(f"♻️  Stale recovery: {recovered} rows reset to pending")

            post = _queue.get_next_post()
            if post:
                _publish_one(post)
                consecutive_errors = 0
                continue

        except (psycopg2.OperationalError, psycopg2.InterfaceError) as exc:
            consecutive_errors += 1
            wait = min(consecutive_errors * 3, 30)
            logger.error(f"⚠️ Publishing worker DB error (#{consecutive_errors}): {exc}")
            time.sleep(wait)
            continue

        except Exception as exc:
            consecutive_errors += 1
            wait = min(consecutive_errors * 3, 30)
            logger.error(
                f"⚠️ Publishing worker error (#{consecutive_errors}): {exc}",
                exc_info=True,
            )
            time.sleep(wait)
            continue

        else:
            consecutive_errors = 0

        time.sleep(3)
