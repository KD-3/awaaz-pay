import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    vobiz_auth_id: str = os.getenv("VOBIZ_AUTH_ID", "")
    vobiz_auth_token: str = os.getenv("VOBIZ_AUTH_TOKEN", "")
    vobiz_api_base: str = os.getenv("VOBIZ_API_BASE", "https://api.vobiz.ai/api/v1")
    vobiz_number: str = os.getenv("VOBIZ_NUMBER", "")

    sarvam_api_key: str = os.getenv("SARVAM_API_KEY", "")
    sarvam_stt_ws_url: str = os.getenv("SARVAM_STT_WS_URL", "wss://api.sarvam.ai/speech-to-text/ws")
    sarvam_tts_ws_url: str = os.getenv("SARVAM_TTS_WS_URL", "wss://api.sarvam.ai/text-to-speech/ws")
    sarvam_chat_url: str = os.getenv("SARVAM_CHAT_URL", "https://api.sarvam.ai/v1/chat/completions")
    sarvam_slot_model: str = os.getenv("SARVAM_SLOT_MODEL", "sarvam-30b")

    db_path: str = os.getenv("DB_PATH", "./awaazpay.db")
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "")
    confidence_gate_threshold: float = float(os.getenv("CONFIDENCE_GATE_THRESHOLD", "0.75"))
    ledger_match_threshold: int = int(os.getenv("LEDGER_MATCH_THRESHOLD", "85"))


settings = Settings()
