"""Autonomous Idle Internet Learning & Training Data Engine for CDX.

When the system is idle (no active user queries for >= 15 seconds), the IdleLearner
autonomously connects to the internet, discovers recent tech news, AI research, and
programming paradigms, synthesizes training data pairs, and updates persistent memory.
"""

import asyncio
import json
import logging
import os
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("codex.learner")

LEARNED_KNOWLEDGE_PATH = Path.home() / ".codex" / "learned_knowledge.json"
TRAINING_DATA_PATH = Path.home() / ".codex" / "training_data.jsonl"

EXPLORATION_TOPICS = [
    "latest artificial intelligence models news",
    "recent breakthroughs in LLM reasoning and inference LPUs",
    "modern web development framework standards 2026",
    "Python 3.13 3.14 performance optimizations and JIT compiler",
    "Linux kernel updates and hardware drivers",
    "state of the art multi-agent consensus protocols",
    "cutting edge cybersecurity defense and zero trust architectures",
    "high throughput asynchronous API design patterns",
    "quantum computing algorithms and post-quantum cryptography",
    "distributed systems scalability and vector databases",
]


class IdleLearner:
    """Autonomous engine that harvests recent web news, AI findings, and builds training data during idle periods."""

    def __init__(self, idle_threshold: float = 15.0):
        self.idle_threshold = idle_threshold
        self.last_interaction = time.time()
        self.is_active = True
        self.is_learning = False
        self.current_topic = ""
        self.total_learned_count = 0
        self.recent_insights: List[Dict[str, Any]] = []
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        # Load existing learned knowledge
        self._load_persisted_knowledge()

    def _load_persisted_knowledge(self) -> None:
        try:
            if LEARNED_KNOWLEDGE_PATH.exists():
                data = json.loads(LEARNED_KNOWLEDGE_PATH.read_text(encoding="utf-8"))
                self.recent_insights = data.get("insights", [])
                self.total_learned_count = data.get("total_learned", len(self.recent_insights))
        except Exception:
            self.recent_insights = []
            self.total_learned_count = 0

    def _save_persisted_knowledge(self) -> None:
        try:
            LEARNED_KNOWLEDGE_PATH.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "total_learned": self.total_learned_count,
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
                "insights": self.recent_insights[-50:],  # keep last 50 insights
            }
            LEARNED_KNOWLEDGE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to persist learned knowledge: {e}")

    def _append_training_sample(self, prompt: str, completion: str, source: str, topic: str) -> None:
        try:
            TRAINING_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
            record = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "topic": topic,
                "source": source,
                "prompt": prompt,
                "completion": completion,
            }
            with open(TRAINING_DATA_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            logger.warning(f"Failed to append training data: {e}")

    def record_interaction(self) -> None:
        """Call whenever a user sends a prompt or interacts with the system."""
        with self._lock:
            self.last_interaction = time.time()
            self.is_learning = False

    def is_idle(self) -> bool:
        """Check if enough idle time has passed without user queries."""
        with self._lock:
            return (time.time() - self.last_interaction) >= self.idle_threshold

    def start_background_daemon(self) -> None:
        """Launch the autonomous learning background thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._daemon_loop, daemon=True, name="CDX-IdleLearner")
        self._thread.start()

    def stop_background_daemon(self) -> None:
        """Stop background worker."""
        self._stop_event.set()

    def _daemon_loop(self) -> None:
        """Background loop continuously polling idle time and triggering learning cycles."""
        topic_idx = 0
        while not self._stop_event.is_set():
            try:
                # Sleep briefly before checking idle state
                time.sleep(3.0)
                if self._stop_event.is_set():
                    break

                if self.is_idle():
                    # Pick alternating between live HackerNews and rotating research topics
                    if topic_idx % 2 == 0:
                        self.learn_recent_news_cycle()
                    else:
                        topic = EXPLORATION_TOPICS[(topic_idx // 2) % len(EXPLORATION_TOPICS)]
                        self.learn_topic_cycle(topic)
                    topic_idx += 1
                    # Cool down between learning cycles to prevent spamming
                    time.sleep(15.0)
            except Exception as e:
                logger.debug(f"Idle learning cycle exception: {e}")
                time.sleep(10.0)

    def learn_recent_news_cycle(self, force: bool = False) -> Dict[str, Any]:
        """Fetch and synthesize top live technology news from Hacker News."""
        with self._lock:
            self.is_learning = True
            self.current_topic = "Live Tech News & Announcements"

        result = {"status": "skipped", "news": []}
        try:
            req = urllib.request.Request(
                "https://hacker-news.firebaseio.com/v0/topstories.json",
                headers={"User-Agent": "Codex-Autonomous-Learner/1.7.0"}
            )
            with urllib.request.urlopen(req, timeout=6.0) as resp:
                top_ids = json.loads(resp.read().decode("utf-8"))[:3]

            news_items = []
            for item_id in top_ids:
                if not force and not self.is_idle():
                    break
                item_req = urllib.request.Request(
                    f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json",
                    headers={"User-Agent": "Codex-Autonomous-Learner/1.7.0"}
                )
                with urllib.request.urlopen(item_req, timeout=4.0) as r:
                    item_data = json.loads(r.read().decode("utf-8"))
                    title = item_data.get("title", "")
                    url = item_data.get("url", f"https://news.ycombinator.com/item?id={item_id}")
                    score = item_data.get("score", 0)
                    if title:
                        news_items.append({"title": title, "url": url, "score": score})

            if news_items:
                with self._lock:
                    for news in news_items:
                        # Check duplicate
                        if any(n.get("title") == news["title"] for n in self.recent_insights):
                            continue
                        insight = {
                            "topic": "Recent Tech News",
                            "title": news["title"],
                            "url": news["url"],
                            "summary": f"Trending developer community discussion (score: {news['score']}): {news['title']}",
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        }
                        self.recent_insights.insert(0, insight)
                        self.total_learned_count += 1

                        # Append fine-tuning / training sample
                        prompt = f"What is the latest tech development regarding: {news['title']}?"
                        completion = f"As recently reported, {news['title']}. Relevant reference: {news['url']}."
                        self._append_training_sample(prompt, completion, news["url"], "Recent Tech News")

                    self._save_persisted_knowledge()
                result = {"status": "success", "learned": len(news_items), "news": news_items}
        except Exception as e:
            result = {"status": "error", "error": str(e)}
        finally:
            with self._lock:
                self.is_learning = False
        return result

    def learn_topic_cycle(self, topic: str, force: bool = False) -> Dict[str, Any]:
        """Perform search query and synthesize training knowledge on a specific computer science topic."""
        with self._lock:
            self.is_learning = True
            self.current_topic = topic

        result = {"status": "skipped", "topic": topic}
        try:
            from codex.tools import execute_web_search
            search_data = execute_web_search(topic)

            if search_data and not search_data.startswith("Error") and len(search_data) > 40:
                summary_snippet = search_data[:600].strip()
                with self._lock:
                    if not any(i.get("title") == topic for i in self.recent_insights):
                        insight = {
                            "topic": "Autonomous Research",
                            "title": topic.title(),
                            "url": "https://duckduckgo.com/?q=" + urllib.parse.quote(topic),
                            "summary": summary_snippet,
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        }
                        self.recent_insights.insert(0, insight)
                        self.total_learned_count += 1

                        # Training sample
                        prompt = f"Synthesize core principles and recent advancements in {topic}."
                        completion = f"Key architectural findings and knowledge for {topic}:\n{summary_snippet}"
                        self._append_training_sample(prompt, completion, "web_search", topic)

                        self._save_persisted_knowledge()
                result = {"status": "success", "topic": topic, "summary": summary_snippet}
        except Exception as e:
            result = {"status": "error", "error": str(e)}
        finally:
            with self._lock:
                self.is_learning = False
        return result

    def get_status(self) -> Dict[str, Any]:
        """Return live telemetry of the learner for API and UI rendering."""
        with self._lock:
            return {
                "active": self.is_active,
                "is_learning": self.is_learning,
                "is_idle": (time.time() - self.last_interaction) >= self.idle_threshold,
                "idle_seconds": round(time.time() - self.last_interaction, 1),
                "current_topic": self.current_topic if self.is_learning else "Standby (Awaiting Idle)",
                "total_learned": self.total_learned_count,
                "recent_insights": self.recent_insights[:10],
                "training_dataset_file": str(TRAINING_DATA_PATH),
            }

    def get_learned_context(self) -> str:
        """Build markdown context injected into the AI's system prompt containing latest learned facts."""
        with self._lock:
            if not self.recent_insights:
                return ""
            lines = [
                "\n### AUTONOMOUSLY LEARNED INTERNET KNOWLEDGE & RECENT NEWS (Real-Time Index):",
                "You have autonomously browsed the web during idle time and acquired the following recent facts:",
            ]
            for item in self.recent_insights[:8]:
                title = item.get("title", "")
                summary = item.get("summary", "")
                ts = item.get("timestamp", "")
                lines.append(f"- **{title}** ({ts}): {summary}")
            lines.append("Use this fresh context naturally whenever answering queries about recent events or current technologies.\n")
            return "\n".join(lines)


# Global singleton instance
idle_learner = IdleLearner(idle_threshold=15.0)
