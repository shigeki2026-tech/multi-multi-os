import json
import os
import threading
from datetime import datetime

import streamlit as st

# Heavy / hardware-dependent imports are deferred to avoid crashing the page
# on environments where PortAudio / audio hardware is unavailable.
try:
    import numpy as np
    import sounddevice as sd
    import soundfile as sf
    _AUDIO_AVAILABLE = True
except Exception as _audio_err:
    _AUDIO_AVAILABLE = False
    _AUDIO_ERROR = str(_audio_err)

from src.ui.bootstrap import ensure_app_ready
from src.ui.session import ensure_logged_in, render_sidebar

SAMPLE_RATE = 44100
CALLER_DEVICE_ID = 2
CALLER_CHANNELS = 2
OPERATOR_DEVICE_ID = 6
OPERATOR_CHANNELS = 1


@st.cache_resource
def load_whisper_model():
    from faster_whisper import WhisperModel
    return WhisperModel("base", device="cpu", compute_type="int8")


def format_time(seconds: float) -> str:
    m = int(seconds // 60)
    s = seconds % 60
    return f"{m:02d}:{s:05.2f}"


def transcribe_file(model, audio_path: str, speaker: str) -> list[dict]:
    segments_gen, _ = model.transcribe(
        audio_path,
        language="ja",
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
    )
    result = []
    for seg in segments_gen:
        text = seg.text.strip()
        if len(text) <= 2:
            continue
        if seg.no_speech_prob >= 0.8:
            continue
        if seg.avg_logprob <= -1.0:
            continue
        result.append({
            "speaker": speaker,
            "start": seg.start,
            "end": seg.end,
            "text": text,
        })
    return result


# ── Page bootstrap ────────────────────────────────────────────────────────────
st.set_page_config(page_title="通話録音", layout="wide")
ensure_app_ready()
user = ensure_logged_in()
render_sidebar(user)

user_id = user["user_id"]
recordings_dir = os.path.join("recordings", str(user_id))
transcripts_dir = os.path.join("transcripts", str(user_id))
os.makedirs(recordings_dir, exist_ok=True)
os.makedirs(transcripts_dir, exist_ok=True)

# ── Session state ─────────────────────────────────────────────────────────────
_defaults = {
    "recording": False,
    "frames_caller": [],
    "frames_operator": [],
    "stop_event": None,
    "stream_caller": None,
    "stream_operator": None,
    "conversation_log": [],
}
for _k, _v in _defaults.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── CSS (デザイントークン準拠) ────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap');

:root {
  --blue-500:    oklch(0.60 0.18 255);
  --blue-600:    oklch(0.52 0.19 255);
  --blue-700:    oklch(0.44 0.17 255);
  --accent-green:oklch(0.68 0.14 155);
  --accent-rose: oklch(0.66 0.17 20);
  --bg:          oklch(0.985 0.004 255);
  --bg-panel:    oklch(1.000 0.000 0);
  --bg-sunken:   oklch(0.965 0.006 255);
  --bg-hover:    oklch(0.955 0.010 255);
  --border:      oklch(0.91 0.008 255);
  --border-strong: oklch(0.84 0.012 255);
  --fg:          oklch(0.22 0.02 255);
  --fg-muted:    oklch(0.48 0.015 255);
  --fg-subtle:   oklch(0.62 0.015 255);
  --shadow-sm:   0 1px 2px 0 oklch(0.2 0.02 255 / 0.04);
  --shadow-md:   0 4px 16px -4px oklch(0.2 0.02 255 / 0.08),
                 0 2px 4px -2px oklch(0.2 0.02 255 / 0.04);
  --radius:      8px;
  --radius-lg:   12px;
}

html, body, [class*="css"] {
  font-family: "Yu Gothic","游ゴシック","YuGothic","Hiragino Sans","Noto Sans JP",sans-serif;
  font-feature-settings: "palt" 1;
  font-size: 13px;
  color: var(--fg);
}

/* ── Recording panel ── */
.rec-panel {
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 1rem 1.25rem;
  box-shadow: var(--shadow-md);
  margin-bottom: 1rem;
}

/* ── Log panel ── */
.log-panel {
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 1.25rem 1.5rem;
  box-shadow: var(--shadow-md);
}

/* ── Speaker card headers ── */
.caller-hdr {
  background: color-mix(in oklch, var(--blue-500) 10%, transparent);
  border: 1px solid color-mix(in oklch, var(--blue-500) 28%, transparent);
  border-radius: var(--radius) var(--radius) 0 0;
  padding: 0.32rem 0.75rem;
  font-size: 10.5px;
  font-weight: 700;
  color: var(--blue-600);
  letter-spacing: 0.02em;
  margin-top: 0.6rem;
  margin-bottom: -0.5rem;
}

.operator-hdr {
  background: color-mix(in oklch, var(--accent-green) 12%, transparent);
  border: 1px solid color-mix(in oklch, var(--accent-green) 28%, transparent);
  border-radius: var(--radius) var(--radius) 0 0;
  padding: 0.32rem 0.75rem;
  font-size: 10.5px;
  font-weight: 700;
  color: var(--accent-green);
  letter-spacing: 0.02em;
  margin-top: 0.6rem;
  margin-bottom: -0.5rem;
}

/* ── Recording dot ── */
.rec-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent-rose);
  animation: blink 1s step-start infinite;
  margin-right: 6px;
  vertical-align: middle;
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.15} }

/* ── Copy button (pill-btn primary style) ── */
.copy-btn {
  height: 32px;
  padding: 0 14px;
  border-radius: var(--radius);
  border: none;
  background: var(--blue-600);
  color: var(--fg-onbrand, #fff);
  font-family: inherit;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.01em;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  white-space: nowrap;
}
.copy-btn:hover { background: var(--blue-700); }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("通話録音・文字起こし")
st.caption("先方音声とオペレーター音声を同時録音し、Whisper で自動文字起こしします。")

if not _AUDIO_AVAILABLE:
    st.error(
        f"⚠️ オーディオライブラリを読み込めませんでした。"
        f"このページはローカル環境（PortAudio が使えるPC）でのみ動作します。\n\n`{_AUDIO_ERROR}`"
    )
    st.stop()

# ── Recording controls ────────────────────────────────────────────────────────
st.markdown('<div class="rec-panel">', unsafe_allow_html=True)
col_status, col_start, col_stop = st.columns([3, 1, 1])

with col_status:
    if st.session_state.recording:
        st.markdown(
            '<span class="rec-dot"></span><b style="color:#DC2626;vertical-align:middle;">録音中...</b>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span style="color:#6B7280;font-size:0.9rem;">⏹ 待機中</span>',
            unsafe_allow_html=True,
        )

with col_start:
    start_btn = st.button(
        "● 録音開始",
        disabled=st.session_state.recording,
        type="primary",
        use_container_width=True,
    )

with col_stop:
    stop_btn = st.button(
        "■ 録音停止",
        disabled=not st.session_state.recording,
        use_container_width=True,
    )

st.markdown("</div>", unsafe_allow_html=True)

# ── Start recording ───────────────────────────────────────────────────────────
if start_btn and not st.session_state.recording:
    frames_caller: list = []
    frames_operator: list = []
    stop_event = threading.Event()

    def _caller_cb(indata, _frames, _time, _status):
        if not stop_event.is_set():
            frames_caller.append(indata.copy())

    def _operator_cb(indata, _frames, _time, _status):
        if not stop_event.is_set():
            frames_operator.append(indata.copy())

    try:
        stream_caller = sd.InputStream(
            device=CALLER_DEVICE_ID,
            channels=CALLER_CHANNELS,
            samplerate=SAMPLE_RATE,
            callback=_caller_cb,
        )
        stream_operator = sd.InputStream(
            device=OPERATOR_DEVICE_ID,
            channels=OPERATOR_CHANNELS,
            samplerate=SAMPLE_RATE,
            callback=_operator_cb,
        )
        stream_caller.start()
        stream_operator.start()
    except Exception as exc:
        st.error(f"録音デバイスの起動に失敗しました: {exc}")
        st.stop()

    st.session_state.recording = True
    st.session_state.frames_caller = frames_caller
    st.session_state.frames_operator = frames_operator
    st.session_state.stop_event = stop_event
    st.session_state.stream_caller = stream_caller
    st.session_state.stream_operator = stream_operator
    st.rerun()

# ── Stop recording & transcribe ───────────────────────────────────────────────
if stop_btn and st.session_state.recording:
    stop_event: threading.Event = st.session_state.stop_event
    stream_caller = st.session_state.stream_caller
    stream_operator = st.session_state.stream_operator
    frames_caller: list = st.session_state.frames_caller
    frames_operator: list = st.session_state.frames_operator

    stop_event.set()
    for _stream in (stream_caller, stream_operator):
        if _stream is not None:
            try:
                _stream.stop()
                _stream.close()
            except Exception:
                pass

    st.session_state.recording = False
    st.session_state.stream_caller = None
    st.session_state.stream_operator = None
    st.session_state.stop_event = None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    wav_paths: dict[str, str] = {}

    if frames_caller:
        caller_audio = np.concatenate(frames_caller, axis=0)
        caller_path = os.path.join(recordings_dir, f"{timestamp}_caller.wav")
        sf.write(caller_path, caller_audio, SAMPLE_RATE)
        wav_paths["先方"] = caller_path

    if frames_operator:
        operator_audio = np.concatenate(frames_operator, axis=0)
        operator_path = os.path.join(recordings_dir, f"{timestamp}_operator.wav")
        sf.write(operator_path, operator_audio, SAMPLE_RATE)
        wav_paths["オペレーター"] = operator_path

    if wav_paths:
        with st.spinner("文字起こし中...（しばらくお待ちください）"):
            model = load_whisper_model()
            all_segs: list[dict] = []
            for speaker, path in wav_paths.items():
                all_segs.extend(transcribe_file(model, path, speaker))

        merged = sorted(all_segs, key=lambda x: x["start"])

        # Clear previous text area session state keys
        for i in range(len(st.session_state.conversation_log)):
            st.session_state.pop(f"log_text_{i}", None)

        st.session_state.conversation_log = merged

        if merged:
            transcript_path = os.path.join(transcripts_dir, f"{timestamp}_transcript.txt")
            with open(transcript_path, "w", encoding="utf-8") as f:
                for entry in merged:
                    f.write(f"[{format_time(entry['start'])}] {entry['speaker']}: {entry['text']}\n")
            st.success(f"文字起こし完了 — {len(merged)} セグメント")
        else:
            st.warning("音声は検出されましたが、文字起こし可能なセグメントがありませんでした。")
    else:
        st.warning("録音データがありませんでした。")

    st.rerun()

# ── Conversation log ──────────────────────────────────────────────────────────
log: list[dict] = st.session_state.conversation_log

if log:
    st.markdown('<div class="log-panel">', unsafe_allow_html=True)
    st.subheader("会話ログ")

    btn_col1, btn_col2, _ = st.columns([1.2, 1, 3.8])

    # Build copy text from current (possibly edited) textarea values
    copy_lines = []
    for i, entry in enumerate(log):
        current_text = st.session_state.get(f"log_text_{i}", entry["text"])
        copy_lines.append(f"[{format_time(entry['start'])}] {entry['speaker']}: {current_text}")
    copy_text = "\n".join(copy_lines)

    with btn_col1:
        st.markdown(
            f"""<button class="copy-btn"
                onclick="navigator.clipboard.writeText({json.dumps(copy_text)})
                    .then(()=>this.textContent='✓ コピー済み')
                    .catch(()=>this.textContent='コピー失敗')">
                📋 ログをコピー
            </button>""",
            unsafe_allow_html=True,
        )

    with btn_col2:
        if st.button("🗑 クリア", use_container_width=True):
            for i in range(len(log)):
                st.session_state.pop(f"log_text_{i}", None)
            st.session_state.conversation_log = []
            st.rerun()

    st.divider()

    for i, entry in enumerate(log):
        is_caller = entry["speaker"] == "先方"
        start_ts = format_time(entry["start"])
        end_ts = format_time(entry["end"])

        if is_caller:
            header_html = (
                f'<div class="caller-hdr">🎧 先方 ｜ {start_ts} → {end_ts}</div>'
            )
        else:
            header_html = (
                f'<div class="operator-hdr">🎤 オペレーター ｜ {start_ts} → {end_ts}</div>'
            )

        st.markdown(header_html, unsafe_allow_html=True)
        st.text_area(
            label="",
            value=entry["text"],
            key=f"log_text_{i}",
            height=80,
            label_visibility="collapsed",
        )

    st.markdown("</div>", unsafe_allow_html=True)
