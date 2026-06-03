
from __future__ import annotations

import asyncio
import time
import traceback
from datetime import datetime, timezone
from typing import Callable, Optional

from config.settings import PRIORITY_THRESHOLD_INSTAGRAM
from DB.db import db_execute
from ML.ai import classify_political, get_template_key
from services.instant_publisher import instant_publish
from services.priority_engine import (
    calculate_final_score,
    log_priority_decision,
)
from services.queue_manager import QueueManager
from utils.logger import logger

_queue = QueueManager()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _resolve_category_and_template(
    article: dict,
) -> tuple[str, str, Optional[int], float]:
    
    source_label = article.get("source_label", "عام")

    if article.get("use_ai", False):
        label, confidence = classify_political(
            article["title"],
            article.get("content"),
        )
        template_key = get_template_key(label)
        category     = "سياسة" if label == 1 else "عام"
        return category, template_key, label, confidence
    else:
        template_key = article.get("template_key") or "عام"
        
        category_map = {
            "رياضة":    "رياضة",
            "فن":       "فن",
            "سياسة":   "سياسة",
            "اقتصاد":   "اقتصاد",
            "سيارات":   "سيارات",
            "تكنولوجيا": "تكنولوجيا",
            "ثقافة":    "ثقافة",
            "عام":      source_label,  
        }
        category = category_map.get(template_key, template_key)
        return category, template_key, None, 1.0


def process_article(
    article: dict,
    template_config: dict,
    generate_image_fn: Callable,
) -> None:
    t_start = time.time()

    try:
        exists = db_execute(
            "SELECT id FROM news WHERE url = %s OR title = %s LIMIT 1",
            (article["url"], article["title"]),
            fetch=True,
        )
        if exists:
            logger.debug(f"⏭️  Duplicate skipped: {article['title'][:60]}")
            return

        category, template_key, ai_label, confidence_val = (
            _resolve_category_and_template(article)
        )

        if template_key not in template_config:
            template_key   = "عام"
            category       = article.get("source_label", "عام")
            confidence_val = 0.0

        processed_at = _now()

        result = db_execute(
            """
            INSERT INTO news (
                title, url, image, category, template_key, confidence, content,
                source_url, source_category, source_label,
                detected_at, scraped_at, inserted_at, processed_at
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),%s)
            ON CONFLICT (url) DO NOTHING
            RETURNING id
            """,
            (
                article["title"],
                article["url"],
                article.get("image"),
                category,
                template_key,
                confidence_val,
                article.get("content"),
                article.get("source_url"),
                article.get("source_name"),
                article.get("source_label"),
                article.get("detected_at"),
                article.get("scraped_at"),
                processed_at,
            ),
            fetch=True,
        )

        if not result:
            logger.warning(f"⏭️  ON CONFLICT skip: {article['title'][:60]}")
            return

        news_id = result["id"] if isinstance(result, dict) else result[0]
        if not news_id:
            logger.error("❌ No news_id from DB insert")
            return

        logger.info(
            f"🟢 [{article.get('source_label','?')}] Saved"
            f" | id={news_id} | cat={category} | tpl={template_key}"
            f" | conf={confidence_val:.2f} | {article['title'][:60]}"
        )

        priority_score = log_priority_decision(
            article["title"], article.get("content") or ""
        )

        
        image_url = generate_image_fn(
            article["title"],
            article.get("image"),
            news_id,
            article["url"],
            template_key,      
            confidence_val,
            article.get("content"),
            send_to_telegram=False,
        )

        if not image_url:
            logger.warning(
                f"⚠️  Image gen returned None for id={news_id} — "
                f"continuing without generated image"
            )

        scores    = calculate_final_score(
            article["title"],
            article.get("content") or "",
            time.time(),
        )
        queued_at  = _now()
        created_ts = time.time()

        _queue.add_or_update_queue_item({
            "article_id":     news_id,
            "title":          article["title"],
            "url":            article["url"],
            "content":        article.get("content"),
            "image_url":      image_url,
            "created_at":     created_ts,
            "detected_at":    article.get("detected_at"),
            "scraped_at":     article.get("scraped_at"),
            "queued_at":      queued_at,
            "priority_score": priority_score,
            "category":       category,
            "template_key":   template_key,
            "source_label":   article.get("source_label"),
            **scores,
        })

        db_execute(
            """
            UPDATE news_queue
            SET image_url       = %s,
                generated_image = %s,
                category        = %s,
                template_key    = %s,
                source_label    = %s,
                queued_at       = NOW()
            WHERE article_id = %s
            """,
            (
                image_url, f"news_{news_id}.jpg",
                category, template_key,
                article.get("source_label"), news_id,
            ),
        )

        db_execute(
            "UPDATE news SET queued_at = NOW() WHERE id = %s",
            (news_id,),
        )

        if ai_label is not None and confidence_val >= 0.65:
            db_execute(
                """
                INSERT INTO confirmed_training (title, label, confidence)
                VALUES (%s, %s, %s)
                ON CONFLICT (title) DO NOTHING
                """,
                (article["title"], ai_label, confidence_val),
            )

        queue_row: dict = {
            "id":             None,
            "article_id":     news_id,
            "title":          article["title"],
            "url":            article["url"],
            "content":        article.get("content"),
            "image_url":      image_url,
            "created_at":     created_ts,
            "priority_score": priority_score,
            "category":       category,
            "template_key":   template_key,
            "source_label":   article.get("source_label"),
            "status":         "pending",
            **scores,
        }

        id_row = db_execute(
            "SELECT id FROM news_queue WHERE article_id = %s LIMIT 1",
            (news_id,),
            fetch=True,
        )
        if not id_row:
            logger.error(f"❌ Queue row not found for article_id={news_id}")
            return

        queue_row["id"] = id_row["id"] if isinstance(id_row, dict) else id_row[0]

        t_total = (time.time() - t_start) * 1000
        logger.info(
            f"⚡ Processed in {t_total:.0f}ms"
            f" | id={news_id} | priority={priority_score}"
            f" | image={'✅' if image_url else '❌'}"
        )

        if priority_score >= PRIORITY_THRESHOLD_INSTAGRAM:
            logger.info(
                f"🚨 HIGH PRIORITY (score={priority_score}) — instant dispatch"
            )
            instant_publish(queue_row)
        else:
            logger.info(
                f"📥 Enqueued for scheduler | id={news_id} | score={priority_score}"
            )

    except Exception as exc:
        logger.error(f"❌ process_article error: {exc}")
        traceback.print_exc()


async def article_consumer(
    in_queue: asyncio.Queue,
    template_config: dict,
    generate_image_fn: Callable,
) -> None:
    loop = asyncio.get_event_loop()
    logger.info("📦 Article consumer started")

    while True:
        try:
            article = await asyncio.wait_for(in_queue.get(), timeout=5.0)
            await loop.run_in_executor(
                None,
                process_article,
                article, template_config, generate_image_fn,
            )
            in_queue.task_done()
        except asyncio.TimeoutError:
            continue
        except Exception as exc:
            logger.error(f"❌ Consumer error: {exc}", exc_info=True)
            await asyncio.sleep(1)


def save_news(
    news: list[dict],
    template_config: dict,
    generate_image_fn: Callable,
) -> None:
    for item in news:
        item.setdefault("source_url",   "https://mnsht.net/category/1")
        item.setdefault("source_name",  "uae")
        item.setdefault("source_label", "الإمارات")
        item.setdefault("template_key", None)
        item.setdefault("use_ai",       True)
        item.setdefault("detected_at",  _now())
        item.setdefault("scraped_at",   _now())
        process_article(item, template_config, generate_image_fn)