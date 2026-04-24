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

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Yu Gothic', 'Noto Sans JP', sans-serif;
}

.rec-panel {
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
    padding: 1.1rem 1.5rem;
    box-shadow: 0 4px 6px rgba(0,0,0,0.07);
    margin-bottom: 1.25rem;
}

.log-panel {
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    box-shadow: 0 4px 6px rgba(0,0,0,0.07);
}

.caller-hdr {
    background: #EFF6FF;
    border: 1px solid #BFDBFE;
    border-radius: 8px 8px 0 0;
    padding: 0.35rem 0.75rem;
    font-size: 0.72rem;
    font-weight: 700;
    color: #1D4ED8;
    margin-top: 0.5rem;
    margin-bottom: -0.5rem;
}

.operator-hdr {
    background: #F0FDF4;
    border: 1px solid #BBF7D0;
    border-radius: 8px 8px 0 0;
    padding: 0.35rem 0.75rem;
    font-size: 0.72rem;
    font-weight: 700;
    color: #15803D;
    margin-top: 0.5rem;
    margin-bottom: -0.5rem;
}

.rec-dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #DC2626;
    animation: blink 1s step-start infinite;
    margin-right: 6px;
    vertical-align: middle;
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.15} }

.copy-btn {
    background: oklch(0.60 0.18 255);
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 0.42rem 1rem;
    cursor: pointer;
    font-family: inherit;
    font-size: 0.875rem;
    font-weight: 600;
    width: 100%;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}
.copy-btn:hover { opacity: 0.9; }
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
