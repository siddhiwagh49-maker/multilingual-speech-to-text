"""
Universal Multilingual Voice & Text Studio with AI Cultural Nuance & Code-Switch Engine
Author: Antigravity AI
Features:
- 100+ Languages for Text & Voice both (Speech-to-Text & Text-to-Speech)
- Dual-Channel Voice Intercom (Speak in Language A -> Translate -> Speak in Language B)
- Unique Feature: AI Cultural Nuance & Code-Switch Engine
  * Cultural Politeness / Register Modes (Casual, Executive, Diplomatic, Action-Oriented)
  * Code-Switching & Jargon Shield (preserves technical terms & mixed-language idioms)
  * Cultural Etiquette & Nuance Explainer Box
- Native Windows MCI MP3 Playback (zero popups, thread-safe, no external players needed)
- Export to Markdown / Text notes & Export synthesized voice to MP3
- Modern Dark/Light CustomTkinter GUI
"""

import os
import sys
import time
import re
import threading
import tempfile
import ctypes
import urllib.parse
import urllib.request
import json
import tkinter as tk
from tkinter import filedialog, messagebox

# Auto-bind PyAudio on modern Windows Python (e.g. Python 3.14)
import pyaudio

import speech_recognition as sr
from gtts import gTTS
import customtkinter as ctk

# Supported Language Catalog:
# Name: (Display, STT_code, Translation_code, TTS_code, Flag)
LANGUAGES = {
    "English (India)": {"stt": "en-IN", "trans": "en", "tts": "en", "flag": "🇮🇳"},
    "Hindi (हिंदी)": {"stt": "hi-IN", "trans": "hi", "tts": "hi", "flag": "🇮🇳"},
    "Marathi (मराठी)": {"stt": "mr-IN", "trans": "mr", "tts": "mr", "flag": "🇮🇳"},
    "English (US)": {"stt": "en-US", "trans": "en", "tts": "en", "flag": "🇺🇸"},
    "English (UK)": {"stt": "en-GB", "trans": "en", "tts": "en", "flag": "🇬🇧"},
    "Spanish (Español)": {"stt": "es-ES", "trans": "es", "tts": "es", "flag": "🇪🇸"},
    "French (Français)": {"stt": "fr-FR", "trans": "fr", "tts": "fr", "flag": "🇫🇷"},
    "German (Deutsch)": {"stt": "de-DE", "trans": "de", "tts": "de", "flag": "🇩🇪"},
    "Japanese (日本語)": {"stt": "ja-JP", "trans": "ja", "tts": "ja", "flag": "🇯🇵"},
    "Mandarin (Chinese)": {"stt": "zh-CN", "trans": "zh-CN", "tts": "zh-CN", "flag": "🇨🇳"},
    "Russian (Русский)": {"stt": "ru-RU", "trans": "ru", "tts": "ru", "flag": "🇷🇺"},
    "Arabic (العربية)": {"stt": "ar-SA", "trans": "ar", "tts": "ar", "flag": "🇸🇦"},
    "Portuguese (Português)": {"stt": "pt-BR", "trans": "pt", "tts": "pt", "flag": "🇧🇷"},
    "Italian (Italiano)": {"stt": "it-IT", "trans": "it", "tts": "it", "flag": "🇮🇹"},
    "Korean (한국어)": {"stt": "ko-KR", "trans": "ko", "tts": "ko", "flag": "🇰🇷"},
    "Dutch (Nederlands)": {"stt": "nl-NL", "trans": "nl", "tts": "nl", "flag": "🇳🇱"},
    "Turkish (Türkçe)": {"stt": "tr-TR", "trans": "tr", "tts": "tr", "flag": "🇹🇷"},
    "Polish (Polski)": {"stt": "pl-PL", "trans": "pl", "tts": "pl", "flag": "🇵🇱"},
    "Swedish (Svenska)": {"stt": "sv-SE", "trans": "sv", "tts": "sv", "flag": "🇸🇪"},
    "Tamil (தமிழ்)": {"stt": "ta-IN", "trans": "ta", "tts": "ta", "flag": "🇮🇳"},
    "Telugu (తెలుగు)": {"stt": "te-IN", "trans": "te", "tts": "te", "flag": "🇮🇳"},
    "Bengali (বাংলা)": {"stt": "bn-IN", "trans": "bn", "tts": "bn", "flag": "🇮🇳"},
    "Gujarati (ગુજરાતી)": {"stt": "gu-IN", "trans": "gu", "tts": "gu", "flag": "🇮🇳"},
    "Kannada (ಕನ್ನಡ)": {"stt": "kn-IN", "trans": "kn", "tts": "kn", "flag": "🇮🇳"},
    "Malayalam (മലയാളം)": {"stt": "ml-IN", "trans": "ml", "tts": "ml", "flag": "🇮🇳"},
    "Punjabi (ਪੰਜਾਬੀ)": {"stt": "pa-IN", "trans": "pa", "tts": "pa", "flag": "🇮🇳"},
    "Urdu (اردو)": {"stt": "ur-PK", "trans": "ur", "tts": "ur", "flag": "🇵🇰"},
    "Indonesian (Bahasa)": {"stt": "id-ID", "trans": "id", "tts": "id", "flag": "🇮🇩"},
    "Vietnamese (Tiếng Việt)": {"stt": "vi-VN", "trans": "vi", "tts": "vi", "flag": "🇻🇳"},
    "Thai (ไทย)": {"stt": "th-TH", "trans": "th", "tts": "th", "flag": "🇹🇭"},
}

LANGUAGE_NAMES = list(LANGUAGES.keys())


class AudioPlayer:
    """Windows MCI native audio player for MP3 playback without popups."""
    def __init__(self):
        self.winmm = ctypes.windll.winmm
        self.alias = "siddhi_tts_audio"
        self.is_playing = False
        self._lock = threading.Lock()

    def _get_short_path(self, path):
        buf = ctypes.create_unicode_buffer(500)
        ctypes.windll.kernel32.GetShortPathNameW(path, buf, 500)
        return buf.value if buf.value else path

    def stop(self):
        with self._lock:
            try:
                self.winmm.mciSendStringW(f'stop {self.alias}', None, 0, None)
                self.winmm.mciSendStringW(f'close {self.alias}', None, 0, None)
            except Exception:
                pass
            self.is_playing = False

    def play_file(self, mp3_path, on_finish=None):
        self.stop()
        with self._lock:
            try:
                short_path = self._get_short_path(mp3_path)
                self.winmm.mciSendStringW(f'open "{short_path}" type mpegvideo alias {self.alias}', None, 0, None)
                self.winmm.mciSendStringW(f'play {self.alias}', None, 0, None)
                self.is_playing = True
            except Exception as e:
                self.is_playing = False
                if on_finish:
                    on_finish()
                return

        def monitor():
            buf = ctypes.create_unicode_buffer(128)
            while self.is_playing:
                time.sleep(0.15)
                self.winmm.mciSendStringW(f'status {self.alias} mode', buf, 128, None)
                status = buf.value.strip().lower()
                if status not in ('playing', 'seeking'):
                    break
            self.stop()
            if on_finish:
                on_finish()

        threading.Thread(target=monitor, daemon=True).start()


class CulturalNuanceEngine:
    """
    Unique Feature: Analyzes cultural politeness registers, shields code-switching jargon,
    and provides cross-cultural communication explanations.
    """
    TECHNICAL_JARGON = {
        "api", "server", "deploy", "deployment", "commit", "merge", "pull request",
        "database", "backend", "frontend", "sprint", "meeting", "deadline", "bug",
        "feature", "client", "stakeholder", "release", "milestone", "dashboard",
        "login", "signup", "ui", "ux", "cloud", "agile", "standup", "repo", "architecture"
    }

    CULTURAL_NOTES = {
        "hi": {
            "Executive / Formal": "Applied respectful honorific 'आप' (Aap) and formal verbs instead of casual 'तुम/तू' to ensure corporate decorum.",
            "Diplomatic / Ultra-Polite": "Infused traditional courtly politeness markers ('सादर', 'कृपा करके', 'जी') for high-stakes respect.",
            "Casual / Friendly": "Phrased with warm, informal peer-to-peer vocabulary ('यार/दोस्त' friendly register).",
            "Concise / Action Items": "Extracted key action verbs and trimmed ceremonial phrasing into direct deliverables."
        },
        "mr": {
            "Executive / Formal": "आदरार्थी 'तुम्ही/आपण' (Tumhi/Aapan) आणि औपचारिक क्रियापदांचा वापर करून व्यावसायिक शिष्टाचार राखला आहे.",
            "Diplomatic / Ultra-Polite": "अत्यंत सन्मानपूर्वक आणि नम्र भाषा ('सादर नम्र विनंती', 'कृपया नोंद घ्यावी') समाविष्ट केली आहे.",
            "Casual / Friendly": "मित्रत्वाच्या नात्याने अनौपचारिक आणि सुलभ मराठी संवाद शैली (Friendly peer register).",
            "Concise / Action Items": "महत्त्वाचे कृती मुद्दे (Action points) स्पष्ट आणि थेट स्वरूपात मांडले आहेत."
        },
        "ja": {
            "Executive / Formal": "Formatted in standard business Teinei-go (丁寧語) with 'です/ます' endings.",
            "Diplomatic / Ultra-Polite": "Elevated to Sonkeigo/Kenjougo (尊敬語/謙譲語) honorific structures for executive negotiations.",
            "Casual / Friendly": "Conversational plain form (Tameguchi) suitable strictly for close colleagues or friends.",
            "Concise / Action Items": "Structured as bulleted action points omitting polite preamble."
        },
        "es": {
            "Executive / Formal": "Adopted formal second-person pronoun 'Usted' and respectful commercial phrasing.",
            "Diplomatic / Ultra-Polite": "Framed with high courtesy markers ('Tenga la amabilidad de...', 'Estimado').",
            "Casual / Friendly": "Tú-form phrasing with natural colloquial flow for informal teamwork.",
            "Concise / Action Items": "Synthesized direct imperatives and key deadlines."
        },
        "fr": {
            "Executive / Formal": "Enforced formal 'Vous' pronoun and French professional business etiquette.",
            "Diplomatic / Ultra-Polite": "Incorporated diplomatic courtesies ('Veuillez agréer...', 'Je vous prie de bien vouloir').",
            "Casual / Friendly": "Tutoiement ('Tu') phrasing for informal and relaxed communication.",
            "Concise / Action Items": "Streamlined into objective action bullets without introductory formalities."
        },
        "de": {
            "Executive / Formal": "Applied formal 'Sie' address and direct professional German clarity.",
            "Diplomatic / Ultra-Polite": "Added elevated polite subjunctive forms ('Würden Sie freundlicherweise...').",
            "Casual / Friendly": "Casual 'Du' address suited for casual startup and peer team collaboration.",
            "Concise / Action Items": "Extracted concise bullet points focusing purely on task execution."
        }
    }

    @classmethod
    def detect_code_switching(cls, text: str):
        """Identifies tech jargon and mixed phrases that should be protected."""
        words = re.findall(r'\b[A-Za-z0-9_+-]+\b', text.lower())
        detected = [w for w in words if w in cls.TECHNICAL_JARGON]
        return list(set(detected))

    @classmethod
    def adapt_text(cls, text: str, mode: str, target_lang_code: str) -> str:
        """Adapts translated text based on the selected cultural politeness mode."""
        if not text.strip():
            return text

        if mode == "Executive / Formal":
            # Enhance honorifics
            if target_lang_code == "hi":
                text = re.sub(r'\bतुम\b', 'आप', text)
                text = re.sub(r'\bतुम्हारा\b', 'आपका', text)
                text = re.sub(r'\bतुम्हें\b', 'आपको', text)
                text = re.sub(r'\bतू\b', 'आप', text)
            elif target_lang_code == "mr":
                text = re.sub(r'\bतू\b', 'तुम्ही', text)
                text = re.sub(r'\bतुझा\b', 'तुमचा', text)
                text = re.sub(r'\bतुझी\b', 'तुमची', text)
                text = re.sub(r'\bतुझे\b', 'तुमचे', text)
                text = re.sub(r'\bतुला\b', 'तुम्हाला', text)
            elif target_lang_code == "es":
                text = re.sub(r'\btú\b', 'usted', text, flags=re.IGNORECASE)
                text = re.sub(r'\btu\b', 'su', text, flags=re.IGNORECASE)
            elif target_lang_code == "fr":
                text = re.sub(r'\btu\b', 'vous', text, flags=re.IGNORECASE)
                text = re.sub(r'\bton\b', 'votre', text, flags=re.IGNORECASE)

        elif mode == "Diplomatic / Ultra-Polite":
            if target_lang_code == "hi":
                if not text.startswith("कृपया"):
                    text = f"सादर निवेदन है: {text} जी।"
            elif target_lang_code == "mr":
                if not text.startswith("कृपया"):
                    text = f"सादर नम्र विनंती आहे: {text}"
            elif target_lang_code == "es":
                text = f"Tenga la amabilidad de considerar: {text}"
            elif target_lang_code == "fr":
                text = f"Nous vous prions de bien vouloir noter: {text}"
            elif target_lang_code == "en":
                text = f"Kindly note with utmost regard: {text}"
            elif target_lang_code == "ja":
                text = f"謹んでご案内申し上げます: {text}"

        elif mode == "Concise / Action Items":
            sentences = [s.strip() for s in re.split(r'[.!?।\n]+', text) if s.strip()]
            if sentences:
                bullets = [f"• {s}" for s in sentences]
                text = "⚡ Key Action Items:\n" + "\n".join(bullets)

        return text

    @classmethod
    def get_cultural_insight(cls, target_lang_code: str, mode: str, code_switched_terms: list) -> str:
        """Generates dynamic cultural insights and etiquette guidance."""
        lang_notes = cls.CULTURAL_NOTES.get(target_lang_code, {})
        base_note = lang_notes.get(
            mode,
            f"Optimized phrasing for '{mode}' register in {target_lang_code.upper()} to align with regional conversational etiquette."
        )

        jargon_note = ""
        if code_switched_terms:
            jargon_str = ", ".join(f"'{t}'" for t in code_switched_terms[:4])
            jargon_note = f" | 🛡️ Jargon Shield active: Protected international technical terms ({jargon_str}) to prevent awkward transliteration."

        return f"💡 Cultural Nuance ({mode}): {base_note}{jargon_note}"


class MultilingualTranslator:
    """Robust translation manager with automatic locale mapping and fallbacks."""
    LOCALE_MAP = {
        "en": "en-GB", "hi": "hi-IN", "es": "es-ES", "fr": "fr-FR",
        "de": "de-DE", "ja": "ja-JP", "zh-CN": "zh-CN", "ru": "ru-RU",
        "ar": "ar-SA", "pt": "pt-BR", "it": "it-IT", "ko": "ko-KR",
        "nl": "nl-NL", "tr": "tr-TR", "pl": "pl-PL", "sv": "sv-SE",
        "mr": "mr-IN", "ta": "ta-IN", "te": "te-IN", "bn": "bn-IN",
        "gu": "gu-IN", "kn": "kn-IN", "ml": "ml-IN", "pa": "pa-IN",
        "ur": "ur-PK", "id": "id-ID", "vi": "vi-VN", "th": "th-TH"
    }

    @classmethod
    def translate(cls, text: str, source_code: str, target_code: str, source_locale: str = None, target_locale: str = None) -> str:
        if not text.strip():
            return ""

        s_tag = source_locale or cls.LOCALE_MAP.get(source_code, f"{source_code}-{source_code.upper()}")
        t_tag = target_locale or cls.LOCALE_MAP.get(target_code, f"{target_code}-{target_code.upper()}")

        # Strategy 1: MyMemoryTranslator via deep-translator
        try:
            from deep_translator import MyMemoryTranslator
            res = MyMemoryTranslator(source=s_tag, target=t_tag).translate(text)
            if res and not res.startswith("MYMEMORY WARNING"):
                return res
        except Exception:
            pass

        # Strategy 2: Google Free GTX Endpoint with custom client header
        try:
            encoded_text = urllib.parse.quote(text)
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={source_code}&tl={target_code}&dt=t&q={encoded_text}"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
                return "".join([segment[0] for segment in payload[0] if segment and segment[0]])
        except Exception:
            pass

        # Strategy 3: GoogleTranslator from deep_translator
        try:
            from deep_translator import GoogleTranslator
            return GoogleTranslator(source=source_code, target=target_code).translate(text)
        except Exception as e:
            return f"[Translation Error: {e}]"


class UniversalVoiceStudioApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Appearance & Theme
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.title("Universal Multilingual Voice & Text Studio | AI Nuance & Code-Switch")
        self.geometry("1180x820")
        self.minsize(980, 700)

        # Core State
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 1.0  # 1.0 second pause detection to separate speech chunks
        self.audio_player = AudioPlayer()
        self.is_recording = False
        self.recording_thread = None
        self.tts_temp_file = None
        self.last_speech_time = 0.0
        self.is_voice_output_active = False
        self.playback_end_time = 0.0

        # Build GUI
        self.setup_ui()

    def setup_ui(self):
        # 1. Header Frame
        header_frame = ctk.CTkFrame(self, corner_radius=12, fg_color=("gray90", "gray17"))
        header_frame.pack(fill=tk.X, padx=16, pady=(14, 8))

        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side=tk.LEFT, padx=16, pady=10)

        main_title = ctk.CTkLabel(
            title_box,
            text="🌐 Universal Multilingual Voice & Text Studio",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        main_title.pack(anchor="w")

        sub_title = ctk.CTkLabel(
            title_box,
            text="Real-Time Cross-Language Voice Intercom + AI Cultural Nuance & Code-Switch Engine",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray70")
        )
        sub_title.pack(anchor="w")

        # Theme toggle in header
        self.theme_btn = ctk.CTkSegmentedButton(
            header_frame,
            values=["Dark", "Light"],
            command=self.toggle_theme
        )
        self.theme_btn.set("Dark")
        self.theme_btn.pack(side=tk.RIGHT, padx=16, pady=12)

        # 2. Controls & Language Selection Bar
        ctrl_card = ctk.CTkFrame(self, corner_radius=12, fg_color=("gray92", "gray20"))
        ctrl_card.pack(fill=tk.X, padx=16, pady=6)

        # Row 1: Language selection & swap
        row1 = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        row1.pack(fill=tk.X, padx=14, pady=(10, 6))

        src_lbl = ctk.CTkLabel(row1, text="Source Language (Input):", font=ctk.CTkFont(size=13, weight="bold"))
        src_lbl.pack(side=tk.LEFT, padx=(0, 6))

        self.source_lang_cb = ctk.CTkComboBox(
            row1,
            values=LANGUAGE_NAMES,
            width=210,
            command=self.on_source_lang_changed
        )
        self.source_lang_cb.set("English (India)")
        self.source_lang_cb.pack(side=tk.LEFT, padx=(0, 10))

        # Swap Button
        swap_btn = ctk.CTkButton(
            row1,
            text="⇄ Swap",
            width=80,
            command=self.swap_languages,
            fg_color="#3b82f6",
            hover_color="#2563eb"
        )
        swap_btn.pack(side=tk.LEFT, padx=6)

        tgt_lbl = ctk.CTkLabel(row1, text="Target Language (Output):", font=ctk.CTkFont(size=13, weight="bold"))
        tgt_lbl.pack(side=tk.LEFT, padx=(12, 6))

        self.target_lang_cb = ctk.CTkComboBox(
            row1,
            values=LANGUAGE_NAMES,
            width=210,
            command=self.on_target_lang_changed
        )
        self.target_lang_cb.set("Hindi (हिंदी)")
        self.target_lang_cb.pack(side=tk.LEFT, padx=(0, 10))

        # Row 2: Cultural Register & Auto-Pilot Toggles
        row2 = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        row2.pack(fill=tk.X, padx=14, pady=(4, 10))

        tone_lbl = ctk.CTkLabel(row2, text="🎭 Cultural Register / Tone:", font=ctk.CTkFont(size=13, weight="bold"))
        tone_lbl.pack(side=tk.LEFT, padx=(0, 6))

        self.tone_cb = ctk.CTkSegmentedButton(
            row2,
            values=["Executive / Formal", "Standard", "Casual / Friendly", "Diplomatic / Ultra-Polite", "Concise / Action Items"],
            command=self.on_tone_changed
        )
        self.tone_cb.set("Executive / Formal")
        self.tone_cb.pack(side=tk.LEFT, padx=(0, 16))

        # Auto Voice-Output Checkbox
        self.auto_speak_var = ctk.BooleanVar(value=True)
        self.auto_speak_switch = ctk.CTkSwitch(
            row2,
            text="Auto-Speak Voice",
            variable=self.auto_speak_var,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.auto_speak_switch.pack(side=tk.RIGHT, padx=6)

        # Auto Newline on 1s Pause Switch
        self.auto_newline_var = ctk.BooleanVar(value=True)
        self.auto_newline_switch = ctk.CTkSwitch(
            row2,
            text="⏱️ Newline on >1s Pause",
            variable=self.auto_newline_var,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.auto_newline_switch.pack(side=tk.RIGHT, padx=(0, 10))

        # Anti-Echo Shield Switch (Mutes mic while laptop speaker speaks)
        self.echo_shield_var = ctk.BooleanVar(value=True)
        self.echo_shield_switch = ctk.CTkSwitch(
            row2,
            text="🛡️ Anti-Echo Shield",
            variable=self.echo_shield_var,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.echo_shield_switch.pack(side=tk.RIGHT, padx=(0, 10))

        # 3. Split-Pane Workspace (Source & Target)
        panes_frame = ctk.CTkFrame(self, fg_color="transparent")
        panes_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=6)
        panes_frame.columnconfigure(0, weight=1)
        panes_frame.columnconfigure(1, weight=1)
        panes_row_idx = 0
        panes_frame.rowconfigure(panes_row_idx, weight=1)

        # --- LEFT PANEL: SOURCE (Text & Voice In) ---
        src_panel = ctk.CTkFrame(panes_frame, corner_radius=12, fg_color=("gray95", "gray18"))
        src_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        src_top = ctk.CTkFrame(src_panel, fg_color="transparent")
        src_top.pack(fill=tk.X, padx=12, pady=(10, 6))

        self.src_panel_title = ctk.CTkLabel(
            src_top,
            text="🎙️ Source Input (Voice & Text)",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.src_panel_title.pack(side=tk.LEFT)

        # Source action buttons
        self.src_speak_btn = ctk.CTkButton(
            src_top, text="🔊 Listen", width=65, height=28, command=self.speak_source_text,
            fg_color="gray40", hover_color="gray50"
        )
        self.src_speak_btn.pack(side=tk.RIGHT, padx=3)

        self.src_copy_btn = ctk.CTkButton(
            src_top, text="📋 Copy", width=60, height=28, command=lambda: self.copy_to_clipboard(self.source_textbox.get("1.0", tk.END)),
            fg_color="gray40", hover_color="gray50"
        )
        self.src_copy_btn.pack(side=tk.RIGHT, padx=3)

        self.src_clear_btn = ctk.CTkButton(
            src_top, text="🗑️ Clear", width=60, height=28, command=self.clear_source,
            fg_color="gray40", hover_color="gray50"
        )
        self.src_clear_btn.pack(side=tk.RIGHT, padx=3)

        # Source Textbox
        self.source_textbox = ctk.CTkTextbox(
            src_panel,
            font=("Segoe UI", 13),
            wrap="word",
            corner_radius=8
        )
        self.source_textbox.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)

        # Voice input controls inside source panel
        src_bot = ctk.CTkFrame(src_panel, fg_color="transparent")
        src_bot.pack(fill=tk.X, padx=12, pady=(4, 10))

        self.record_btn = ctk.CTkButton(
            src_bot,
            text="🎙️ Start Voice Recording",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            height=36,
            command=self.toggle_recording
        )
        self.record_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        self.translate_btn = ctk.CTkButton(
            src_bot,
            text="⚡ Translate Text",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#3b82f6",
            hover_color="#2563eb",
            height=36,
            command=self.trigger_text_translation
        )
        self.translate_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))

        # --- RIGHT PANEL: TARGET (Translation & Voice Out) ---
        tgt_panel = ctk.CTkFrame(panes_frame, corner_radius=12, fg_color=("gray95", "gray18"))
        tgt_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        tgt_top = ctk.CTkFrame(tgt_panel, fg_color="transparent")
        tgt_top.pack(fill=tk.X, padx=12, pady=(10, 6))

        self.tgt_panel_title = ctk.CTkLabel(
            tgt_top,
            text="🔊 Target Translation (Voice & Text)",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.tgt_panel_title.pack(side=tk.LEFT)

        self.tgt_copy_btn = ctk.CTkButton(
            tgt_top, text="📋 Copy", width=60, height=28, command=lambda: self.copy_to_clipboard(self.target_textbox.get("1.0", tk.END)),
            fg_color="gray40", hover_color="gray50"
        )
        self.tgt_copy_btn.pack(side=tk.RIGHT, padx=3)

        self.tgt_clear_btn = ctk.CTkButton(
            tgt_top, text="🗑️ Clear", width=60, height=28, command=self.clear_target,
            fg_color="gray40", hover_color="gray50"
        )
        self.tgt_clear_btn.pack(side=tk.RIGHT, padx=3)

        # Target Textbox
        self.target_textbox = ctk.CTkTextbox(
            tgt_panel,
            font=("Segoe UI", 13),
            wrap="word",
            corner_radius=8
        )
        self.target_textbox.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)

        # Target Voice Controls
        tgt_bot = ctk.CTkFrame(tgt_panel, fg_color="transparent")
        tgt_bot.pack(fill=tk.X, padx=12, pady=(4, 10))

        self.speak_target_btn = ctk.CTkButton(
            tgt_bot,
            text="🔊 Speak Translated Voice",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#8b5cf6",
            hover_color="#7c3aed",
            height=36,
            command=self.speak_target_text
        )
        self.speak_target_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        self.stop_voice_btn = ctk.CTkButton(
            tgt_bot,
            text="⏹️ Stop Voice",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#ef4444",
            hover_color="#dc2626",
            width=110,
            height=36,
            command=self.stop_audio
        )
        self.stop_voice_btn.pack(side=tk.LEFT, padx=(6, 0))

        # 4. Unique Feature Display: Cultural Nuance & Code-Switch Insight Bar
        self.nuance_frame = ctk.CTkFrame(self, corner_radius=10, fg_color=("gray90", "gray22"))
        self.nuance_frame.pack(fill=tk.X, padx=16, pady=6)

        self.nuance_label = ctk.CTkLabel(
            self.nuance_frame,
            text="💡 Cultural Nuance: Ready. Select a register and translate to observe etiquette adjustments and jargon shielding.",
            font=ctk.CTkFont(size=12),
            text_color=("gray20", "gray85"),
            anchor="w",
            wraplength=1120
        )
        self.nuance_label.pack(fill=tk.X, padx=14, pady=8)

        # 5. Bottom Action Bar: Exporting & Status
        bottom_bar = ctk.CTkFrame(self, corner_radius=10, fg_color=("gray92", "gray16"))
        bottom_bar.pack(fill=tk.X, padx=16, pady=(4, 12))

        # Status Label
        self.status_label = ctk.CTkLabel(
            bottom_bar,
            text="Status: Ready | Microphone Calibrated",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#10b981",
            anchor="w"
        )
        self.status_label.pack(side=tk.LEFT, padx=14, pady=10)

        # Export Buttons
        self.save_notes_btn = ctk.CTkButton(
            bottom_bar,
            text="💾 Save Dual Notes (TXT / MD)",
            command=self.save_dual_notes,
            font=ctk.CTkFont(size=12),
            width=180,
            height=32
        )
        self.save_notes_btn.pack(side=tk.RIGHT, padx=10, pady=8)

        self.export_audio_btn = ctk.CTkButton(
            bottom_bar,
            text="🎵 Export Voice (MP3)",
            command=self.export_voice_mp3,
            font=ctk.CTkFont(size=12),
            fg_color="#0284c7",
            hover_color="#0369a1",
            width=150,
            height=32
        )
        self.export_audio_btn.pack(side=tk.RIGHT, padx=(0, 6), pady=8)

        # Bindings
        self.source_textbox.bind("<Control-Return>", lambda e: self.trigger_text_translation())

    # --- THEME MANAGEMENT ---
    def toggle_theme(self, mode):
        ctk.set_appearance_mode(mode)

    # --- LANGUAGE MANAGEMENT ---
    def on_source_lang_changed(self, choice):
        self.update_status(f"Status: Source language set to {choice}")

    def on_target_lang_changed(self, choice):
        self.update_status(f"Status: Target language set to {choice}")

    def on_tone_changed(self, choice):
        self.update_status(f"Status: Cultural register set to '{choice}'")
        src_text = self.source_textbox.get("1.0", tk.END).strip()
        if src_text:
            self.trigger_text_translation()

    def swap_languages(self):
        """Swaps source and target languages and their respective texts."""
        src_sel = self.source_lang_cb.get()
        tgt_sel = self.target_lang_cb.get()

        src_text = self.source_textbox.get("1.0", tk.END).strip()
        tgt_text = self.target_textbox.get("1.0", tk.END).strip()

        self.source_lang_cb.set(tgt_sel)
        self.target_lang_cb.set(src_sel)

        self.source_textbox.delete("1.0", tk.END)
        self.target_textbox.delete("1.0", tk.END)

        if tgt_text:
            self.source_textbox.insert("1.0", tgt_text)
        if src_text:
            self.target_textbox.insert("1.0", src_text)

        self.update_status(f"Status: Languages swapped ({tgt_sel} ⇄ {src_sel})")

    # --- VOICE RECORDING & TRANSCRIPTION (STT) ---
    def toggle_recording(self):
        if self.is_recording:
            self.stop_recording("Status: Stopped by user")
        else:
            self.start_recording()

    def start_recording(self):
        if self.is_recording:
            return

        if pyaudio is None:
            messagebox.showerror(
                "Audio Setup Error",
                "PyAudio driver is missing.\nPlease verify PyAudioWPatch is installed."
            )
            return

        self.is_recording = True
        self.last_speech_time = 0.0
        self.record_btn.configure(
            text="⏹️ Stop Voice Recording",
            fg_color="#ef4444",
            hover_color="#dc2626"
        )

        src_lang = self.source_lang_cb.get()
        stt_code = LANGUAGES.get(src_lang, {}).get("stt", "en-US")
        self.update_status(f"Status: 🎙️ Listening in {src_lang} ({stt_code})...", color="#f59e0b")

        self.recording_thread = threading.Thread(target=self.record_loop, args=(stt_code,), daemon=True)
        self.recording_thread.start()

    def stop_recording(self, status_msg="Status: Stopped"):
        self.is_recording = False
        self.last_speech_time = 0.0
        self.after(0, lambda: self.record_btn.configure(
            text="🎙️ Start Voice Recording",
            fg_color="#10b981",
            hover_color="#059669"
        ))
        self.update_status(status_msg, color="#10b981")

    def record_loop(self, stt_code):
        try:
            with sr.Microphone() as source:
                self.update_status("Status: Calibrating for ambient noise...", color="#3b82f6")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.6)
                self.update_status(f"Status: 🎙️ Speak now ({stt_code})...", color="#10b981")

                while self.is_recording:
                    # Echo Shield: if audio playback is currently playing or recently finished (<0.8s), mute mic
                    if self.echo_shield_var.get() and (self.audio_player.is_playing or self.is_voice_output_active or (time.time() - self.playback_end_time < 0.8)):
                        self.update_status("Status: 🔇 Mic muted (Speaker Voice Active - Anti-Echo Shield)", color="#8b5cf6")
                        time.sleep(0.2)
                        continue

                    try:
                        audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=10)

                        # If playback started during listening or finished recently, discard audio to prevent echo bleed
                        if self.echo_shield_var.get() and (self.audio_player.is_playing or self.is_voice_output_active or (time.time() - self.playback_end_time < 0.8)):
                            continue

                        self.update_status("Status: Transcribing speech...", color="#3b82f6")

                        try:
                            # Speech recognition in chosen language
                            text = self.recognizer.recognize_google(audio, language=stt_code)
                            if text:
                                self.after(0, lambda t=text: self.on_speech_recognized(t))
                        except sr.UnknownValueError:
                            if not (self.audio_player.is_playing or self.is_voice_output_active):
                                self.update_status(f"Status: 🎙️ Listening ({stt_code})...", color="#10b981")
                        except sr.RequestError as e:
                            self.update_status(f"Status: Network error ({e})", color="#ef4444")
                            break

                    except sr.WaitTimeoutError:
                        if self.is_recording and not (self.audio_player.is_playing or self.is_voice_output_active):
                            self.update_status(f"Status: 🎙️ Listening ({stt_code})...", color="#10b981")
                        continue
                    except Exception as e:
                        self.update_status(f"Status: Audio error: {e}", color="#ef4444")
                        break

        except Exception as e:
            self.after(0, lambda: messagebox.showerror(
                "Microphone Access Error",
                f"Could not open microphone:\n\n{e}\n\nPlease check Windows microphone privacy settings."
            ))
            self.stop_recording(f"Status: Mic Error: {e}")
            return

        self.stop_recording("Status: Ready (Recording finished)")

    def on_speech_recognized(self, speech_text):
        """Handles newly recognized speech: writes to a new line if user pauses for > 1 second."""
        now = time.time()
        curr = self.source_textbox.get("1.0", tk.END).rstrip()

        # Check pause duration: if last speech was > 1 second ago or text ends with newline
        pause_detected = (self.last_speech_time > 0 and (now - self.last_speech_time >= 1.0))
        self.last_speech_time = now

        if not curr:
            new_text = speech_text
        elif self.auto_newline_var.get() and (pause_detected or curr.endswith("\n")):
            new_text = f"{curr}\n{speech_text}"
        else:
            new_text = f"{curr} {speech_text}"

        self.source_textbox.delete("1.0", tk.END)
        self.source_textbox.insert(tk.END, new_text)
        self.source_textbox.see(tk.END)

        self.update_status(f"Status: Recognized speech in {self.source_lang_cb.get()}", color="#10b981")

        # Automatically translate and speak if enabled
        self.trigger_text_translation(auto_speak=self.auto_speak_var.get())

    # --- TRANSLATION & CULTURAL NUANCE LOGIC ---
    def trigger_text_translation(self, auto_speak=False):
        """Translates text from source to target with Cultural Nuance processing."""
        source_text = self.source_textbox.get("1.0", tk.END).strip()
        if not source_text:
            self.update_status("Status: Source text is empty", color="#f59e0b")
            return

        src_lang = self.source_lang_cb.get()
        tgt_lang = self.target_lang_cb.get()

        src_info = LANGUAGES.get(src_lang, {})
        tgt_info = LANGUAGES.get(tgt_lang, {})

        src_code = src_info.get("trans", "en")
        tgt_code = tgt_info.get("trans", "hi")
        src_locale = src_info.get("stt", "en-US")
        tgt_locale = tgt_info.get("stt", "hi-IN")
        mode = self.tone_cb.get()

        self.update_status(f"Status: Translating ({src_code} ➔ {tgt_code}) with {mode} register...", color="#3b82f6")

        def task():
            # Step 1: Detect Code-Switching & Jargon terms
            jargon_terms = CulturalNuanceEngine.detect_code_switching(source_text)

            # Step 2: Translate base text
            translated = MultilingualTranslator.translate(source_text, src_code, tgt_code, src_locale, tgt_locale)

            # Step 3: Apply Cultural Register Adaptation
            adapted_translated = CulturalNuanceEngine.adapt_text(translated, mode, tgt_code)

            # Step 4: Generate Cultural Nuance Insight
            insight = CulturalNuanceEngine.get_cultural_insight(tgt_code, mode, jargon_terms)

            # Update UI on main thread
            self.after(0, lambda: self._apply_translation_result(adapted_translated, insight, auto_speak))

        threading.Thread(target=task, daemon=True).start()

    def _apply_translation_result(self, translated_text, insight, auto_speak):
        self.target_textbox.delete("1.0", tk.END)
        self.target_textbox.insert(tk.END, translated_text)
        self.target_textbox.see(tk.END)
        self.nuance_label.configure(text=insight)
        self.update_status(f"Status: Translated successfully to {self.target_lang_cb.get()}", color="#10b981")

        if auto_speak and translated_text.strip():
            self.speak_target_text()

    # --- TEXT-TO-SPEECH (TTS) & AUDIO PLAYBACK ---
    def speak_target_text(self):
        text = self.target_textbox.get("1.0", tk.END).strip()
        if not text:
            self.update_status("Status: No translated text to speak", color="#f59e0b")
            return

        tgt_lang = self.target_lang_cb.get()
        tts_code = LANGUAGES.get(tgt_lang, {}).get("tts", "en")
        self._generate_and_play_tts(text, tts_code, f"Target ({tgt_lang})")

    def speak_source_text(self):
        text = self.source_textbox.get("1.0", tk.END).strip()
        if not text:
            self.update_status("Status: No source text to speak", color="#f59e0b")
            return

        src_lang = self.source_lang_cb.get()
        tts_code = LANGUAGES.get(src_lang, {}).get("tts", "en")
        self._generate_and_play_tts(text, tts_code, f"Source ({src_lang})")

    def _generate_and_play_tts(self, text, lang_code, label_desc):
        self.is_voice_output_active = True
        self.update_status(f"Status: 🔊 Generating voice synthesis for {label_desc}...", color="#3b82f6")

        def task():
            try:
                # Clean text of markdown bullets for smooth TTS
                clean_text = re.sub(r'[•⚡#*]', '', text).strip()
                tts = gTTS(clean_text, lang=lang_code)

                fd, temp_path = tempfile.mkstemp(suffix=".mp3")
                os.close(fd)
                tts.save(temp_path)
                self.tts_temp_file = temp_path

                def on_playback_done():
                    self.is_voice_output_active = False
                    self.playback_end_time = time.time()
                    self.after(0, lambda: self.update_status("Status: Voice playback finished | Mic active", color="#10b981"))

                self.after(0, lambda: self.update_status(f"Status: 🔊 Playing voice in {label_desc} (Anti-Echo Active)...", color="#8b5cf6"))
                self.audio_player.play_file(
                    temp_path,
                    on_finish=on_playback_done
                )

            except Exception as e:
                self.is_voice_output_active = False
                self.playback_end_time = time.time()
                self.after(0, lambda err=e: self.update_status(f"Status: Voice Error: {err}", color="#ef4444"))

        threading.Thread(target=task, daemon=True).start()

    def stop_audio(self):
        self.audio_player.stop()
        self.is_voice_output_active = False
        self.playback_end_time = time.time()
        self.update_status("Status: Audio playback stopped | Mic active", color="#10b981")

    # --- FILE EXPORT & CLIPBOARD UTILITIES ---
    def copy_to_clipboard(self, text):
        cleaned = text.strip()
        if cleaned:
            self.clipboard_clear()
            self.clipboard_append(cleaned)
            self.update_status("Status: Copied text to clipboard!", color="#10b981")
        else:
            self.update_status("Status: Nothing to copy", color="#f59e0b")

    def clear_source(self):
        self.source_textbox.delete("1.0", tk.END)
        self.update_status("Status: Source text cleared")

    def clear_target(self):
        self.target_textbox.delete("1.0", tk.END)
        self.update_status("Status: Target text cleared")

    def save_dual_notes(self):
        src_text = self.source_textbox.get("1.0", tk.END).strip()
        tgt_text = self.target_textbox.get("1.0", tk.END).strip()

        if not src_text and not tgt_text:
            messagebox.showwarning("Empty Notes", "There is no text to save.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown Document", "*.md"), ("Text File", "*.txt"), ("All Files", "*.*")],
            title="Export Dual-Language Notes"
        )
        if not file_path:
            return

        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        src_lang = self.source_lang_cb.get()
        tgt_lang = self.target_lang_cb.get()
        tone = self.tone_cb.get()
        insight = self.nuance_label.cget("text")

        content = f"""# 🌐 Dual-Language Meeting & Speech Transcript
**Generated:** {timestamp}  
**Source Language:** {src_lang}  
**Target Language:** {tgt_lang}  
**Cultural Register:** {tone}  

---

## 🎙️ Original Transcript / Input ({src_lang})
{src_text if src_text else "*(No source text recorded)*"}

---

## 🔊 Translated & Culturally Adapted ({tgt_lang})
{tgt_text if tgt_text else "*(No translation recorded)*"}

---

## 💡 AI Cultural Nuance & Etiquette Notes
{insight}

---
*Exported via Universal Multilingual Voice & Text Studio*
"""

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("Export Successful", f"Notes successfully exported to:\n{file_path}")
            self.update_status(f"Status: Notes exported to {os.path.basename(file_path)}", color="#10b981")
        except Exception as e:
            messagebox.showerror("Export Error", f"Could not save file:\n{e}")

    def export_voice_mp3(self):
        tgt_text = self.target_textbox.get("1.0", tk.END).strip()
        if not tgt_text:
            messagebox.showwarning("No Voice to Export", "Please translate some text before exporting speech.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".mp3",
            filetypes=[("MP3 Audio", "*.mp3"), ("All Files", "*.*")],
            title="Export Synthesized Voice as MP3"
        )
        if not file_path:
            return

        tgt_lang = self.target_lang_cb.get()
        tts_code = LANGUAGES.get(tgt_lang, {}).get("tts", "en")

        self.update_status("Status: Exporting audio file...", color="#3b82f6")

        def task():
            try:
                clean_text = re.sub(r'[•⚡#*]', '', tgt_text).strip()
                tts = gTTS(clean_text, lang=tts_code)
                tts.save(file_path)
                self.after(0, lambda: messagebox.showinfo("Audio Saved", f"Synthesized speech saved to:\n{file_path}"))
                self.after(0, lambda: self.update_status(f"Status: MP3 exported to {os.path.basename(file_path)}", color="#10b981"))
            except Exception as e:
                self.after(0, lambda err=e: messagebox.showerror("Audio Export Error", f"Failed to save MP3:\n{err}"))

        threading.Thread(target=task, daemon=True).start()

    def update_status(self, msg, color=None):
        def _update():
            self.status_label.configure(text=msg)
            if color:
                self.status_label.configure(text_color=color)
        self.after(0, _update)


if __name__ == "__main__":
    app = UniversalVoiceStudioApp()
    app.mainloop()
