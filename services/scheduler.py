
from __future__ import annotations

import time
import logging

from config.settings import ENABLE_FACEBOOK_POSTING
from services.queue_manager import QueueManager
from services.publish_pipeline import PublishPipeline
import psycopg2
from DB.db import db_execute
from utils.logger import logger

_queue    = QueueManager()
_pipeline = PublishPipeline()


def _publish_one(post: dict) -> None:
    post_id    = post["id"]
    title_snip = (post.get("title") or "")[:60]

    age_hours = (time.time() - (post.get("created_at") or time.time())) / 3600
    if age_hours > 3:
        logger.warning(
            f"⏰ Overdue article | id={post_id} | age={age_hours:.1f}h | {title_snip}"
        )

    # Check which platforms still need publishing
    tg_done = post.get("telegram_status")  == "sent"
    ig_done = post.get("instagram_status") in ("sent", "skipped:high_priority_policy",
                                                "skipped:normal_priority_policy",
                                                "skipped:already_published")
    fb_done = post.get("facebook_status")  in ("sent", "skipped:high_priority_policy",
                                                "skipped:normal_priority_policy",
                                                "skipped:fb_disabled",
                                                "skipped:already_published")
    tw_done = post.get("twitter_status")   in ("sent", "skipped:high_priority_policy",
                                                "skipped:normal_priority_policy",
                                                "skipped:already_published")

    if tg_done and ig_done and fb_done and tw_done:

        logger.debug(f"✅ All platforms done (worker skip) | id={post_id}")
        db_execute(
            """
            UPDATE news_queue
            SET status = 'published', published_at = NOW(), last_updated = NOW()
            WHERE id = %s AND status = 'processing'
            """,
            (post_id,),
        )
        return


    results = _pipeline.publish(post)

    tg_status = results.get("telegram",  post.get("telegram_status",  "pending"))
    ig_status = results.get("instagram", post.get("instagram_status", "skipped"))
    fb_status = results.get("facebook",  post.get("facebook_status",  "pending"))
    tw_status = results.get("twitter",   post.get("twitter_status",   "pending"))

    db_execute(
        """
        UPDATE news_queue
        SET
            status           = 'published',
            telegram_status  = %s,
            instagram_status = %s,
            twitter_status   = %s,
            facebook_status  = %s,
            published_at     = NOW(),
            last_updated     = NOW()
        WHERE id = %s AND status = 'processing'
        """,
        (tg_status, ig_status, tw_status, fb_status, post_id),
    )

    logger.info(
        f"✅ Worker published | id={post_id} "
        f"tg={tg_status} ig={ig_status} tw={tw_status} fb={fb_status}"
    )


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
            consecutive_errors = 0  # reset counter on success

        time.sleep(3)
