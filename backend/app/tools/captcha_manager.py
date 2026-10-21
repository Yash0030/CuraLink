"""In-memory CAPTCHA management with asyncio.Event human-in-the-loop gating.

Implements safety rules:
- Agent NEVER solves or bypasses CAPTCHA.
- Pauses with in-memory asyncio.Event gate (live browser cannot be checkpointed).
- Captures screenshot of challenge for UI display.
- Relays human answer or handles Browserbase live view "I solved it".
- Supports up to 3 attempts and configurable timeout.
"""

import asyncio
import time
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class CaptchaSession:
    def __init__(self, run_id: str, lab: str, screenshot_bytes: bytes, live_view_url: Optional[str] = None):
        self.run_id = run_id
        self.lab = lab
        self.screenshot_bytes = screenshot_bytes
        self.live_view_url = live_view_url
        self.event = asyncio.Event()
        self.answer: Optional[str] = None
        self.solved_in_live_view: bool = False
        self.attempts: int = 0
        self.created_at = time.time()

# Key: (run_id, lab) -> CaptchaSession
_ACTIVE_CAPTCHAS: Dict[Tuple[str, str], CaptchaSession] = {}

class CaptchaManager:
    @staticmethod
    def register(run_id: str, lab: str, screenshot_bytes: bytes, live_view_url: Optional[str] = None) -> CaptchaSession:
        key = (run_id, lab)
        session = CaptchaSession(run_id, lab, screenshot_bytes, live_view_url)
        _ACTIVE_CAPTCHAS[key] = session
        logger.info(f"Registered CAPTCHA challenge for run {run_id}, lab {lab}")
        return session

    @staticmethod
    def get_image(run_id: str, lab: str) -> Optional[bytes]:
        session = _ACTIVE_CAPTCHAS.get((run_id, lab))
        return session.screenshot_bytes if session else None

    @staticmethod
    def get_session(run_id: str, lab: str) -> Optional[CaptchaSession]:
        return _ACTIVE_CAPTCHAS.get((run_id, lab))

    @staticmethod
    def get_active_labs_for_run(run_id: str) -> list[str]:
        return [lab for (r_id, lab) in _ACTIVE_CAPTCHAS.keys() if r_id == run_id]

    @staticmethod
    def submit_answer(run_id: str, lab: str, answer: str) -> bool:
        session = _ACTIVE_CAPTCHAS.get((run_id, lab))
        if session:
            session.answer = answer
            session.solved_in_live_view = False
            session.event.set()
            logger.info(f"Relayed human CAPTCHA answer for run {run_id}, lab {lab}")
            return True
        return False

    @staticmethod
    def submit_solved_live(run_id: str, lab: str) -> bool:
        session = _ACTIVE_CAPTCHAS.get((run_id, lab))
        if session:
            session.solved_in_live_view = True
            session.answer = None
            session.event.set()
            logger.info(f"Marked CAPTCHA as solved in live view for run {run_id}, lab {lab}")
            return True
        return False

    @staticmethod
    async def wait_for_resolution(
        session: CaptchaSession,
        timeout_seconds: int = 120
    ) -> Tuple[Optional[str], bool]:
        """Waits on asyncio.Event until human supplies answer or solves in live view.

        Returns:
            (answer_string, solved_in_live_view_bool)
        Raises:
            asyncio.TimeoutError if timeout expires without resolution.
        """
        try:
            session.attempts += 1
            await asyncio.wait_for(session.event.wait(), timeout=timeout_seconds)
            return session.answer, session.solved_in_live_view
        finally:
            # Reset event for next attempt if needed
            session.event.clear()

    @staticmethod
    def unregister(run_id: str, lab: str):
        key = (run_id, lab)
        if key in _ACTIVE_CAPTCHAS:
            del _ACTIVE_CAPTCHAS[key]
            logger.info(f"Unregistered CAPTCHA challenge for run {run_id}, lab {lab}")
