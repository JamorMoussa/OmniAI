import { FormEvent, MouseEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity, AudioLines, BookOpen, ChevronDown, ChevronsUpDown, CircleHelp, Clock3,
  Download, Gauge, KeyRound, Menu, Moon, PanelLeftClose, Play,
  RotateCcw, Search, Send, Settings2, Sparkles, Square, Volume2, X,
} from "lucide-react";
import { getVoices, streamSpeech } from "./api";

const model = "kokoro";
const fallbackVoices = ["af_heart", "af_bella", "af_sarah", "am_adam", "am_michael"];

type Generation = { id: number; text: string; voice: string; url: string; createdAt: Date };

function encodeWav(chunks: Float32Array[], sampleRate: number) {
  const length = chunks.reduce((total, chunk) => total + chunk.length, 0);
  const buffer = new ArrayBuffer(44 + length * 2);
  const view = new DataView(buffer);
  const write = (offset: number, value: string) => [...value].forEach((char, index) => view.setUint8(offset + index, char.charCodeAt(0)));
  write(0, "RIFF"); view.setUint32(4, 36 + length * 2, true); write(8, "WAVE"); write(12, "fmt ");
  view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true); view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true); view.setUint16(34, 16, true); write(36, "data"); view.setUint32(40, length * 2, true);
  let offset = 44;
  chunks.forEach((chunk) => chunk.forEach((sample) => { view.setInt16(offset, Math.max(-1, Math.min(1, sample)) * 0x7fff, true); offset += 2; }));
  return new Blob([buffer], { type: "audio/wav" });
}

function prettyVoice(voice: string) {
  return voice.replace(/^[a-z]{2}_/, "").replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [settingsOpen, setSettingsOpen] = useState(true);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [input, setInput] = useState("");
  const [voices, setVoices] = useState(fallbackVoices);
  const [voice, setVoice] = useState("af_heart");
  const [speed, setSpeed] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [generations, setGenerations] = useState<Generation[]>([]);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [liveBars, setLiveBars] = useState<number[]>([]);
  const audioRef = useRef<HTMLAudioElement>(null);
  const waveformRef = useRef<HTMLDivElement>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const mediaSourceRef = useRef<MediaElementAudioSourceNode | null>(null);
  const animationRef = useRef<number | null>(null);
  const streamTimingRef = useRef<{ start: number; duration: number } | null>(null);
  const streamSourcesRef = useRef<Set<AudioBufferSourceNode>>(new Set());
  const playbackTimeoutRef = useRef<number | null>(null);
  const generatingRef = useRef(false);

  const current = generations[0];
  const characterCount = input.length;

  useEffect(() => {
    const controller = new AbortController();
    getVoices(model, controller.signal)
      .then((items) => {
        if (items.length) {
          setVoices(items);
          setVoice((selected) => items.includes(selected) ? selected : items[0]);
        }
      })
      .catch((reason) => {
        if (reason.name !== "AbortError") setError("Studio couldn't reach the voice API. You can still explore the interface.");
      });
    return () => controller.abort();
  }, []);

  const bars = useMemo(() => Array.from({ length: 64 }, (_, i) => 14 + ((i * 17 + 9) % 38)), []);

  useEffect(() => {
    setProgress(0);
    setCurrentTime(0);
    setDuration(0);
    setLiveBars([]);
  }, [current?.id]);

  useEffect(() => () => {
    if (animationRef.current !== null) cancelAnimationFrame(animationRef.current);
    if (playbackTimeoutRef.current !== null) window.clearTimeout(playbackTimeoutRef.current);
    streamSourcesRef.current.forEach((source) => {
      try { source.stop(); } catch { /* The source has already ended. */ }
    });
    void audioContextRef.current?.close();
  }, []);

  async function generate(event?: FormEvent) {
    event?.preventDefault();
    if (!input.trim() || generatingRef.current) return;
    generatingRef.current = true;
    setLoading(true);
    setError("");
    let generationId: number | null = null;
    try {
      stopAllPlayback();
      const id = Date.now();
      generationId = id;
      const text = input.trim();
      const generation = { id, text, voice, url: "", createdAt: new Date() };
      setGenerations((items) => [generation, ...items]);
      setInput("");
      const context = ensureAudioGraph();
      await context.resume();
      const pcmChunks: Float32Array[] = [];
      let sampleRate = 24_000;
      let nextStart = context.currentTime + .08;
      let streamStarted = false;
      streamTimingRef.current = { start: nextStart, duration: 0 };

      await streamSpeech(text, model, voice, async (wav) => {
        const decoded = await context.decodeAudioData(wav.slice(0));
        sampleRate = decoded.sampleRate;
        pcmChunks.push(new Float32Array(decoded.getChannelData(0)));
        const source = context.createBufferSource();
        source.buffer = decoded;
        source.connect(analyserRef.current!);
        const scheduledAt = Math.max(nextStart, context.currentTime + .04);
        source.start(scheduledAt);
        nextStart = scheduledAt + decoded.duration;
        streamSourcesRef.current.add(source);
        source.onended = () => streamSourcesRef.current.delete(source);
        streamTimingRef.current!.duration += decoded.duration;
        setDuration(streamTimingRef.current!.duration);
        if (!streamStarted) {
          streamStarted = true;
          setPlaying(true);
          startVisualization(false);
        }
      });

      const url = URL.createObjectURL(encodeWav(pcmChunks, sampleRate));
      setGenerations((items) => items.map((item) => item.id === id ? { ...item, url } : item));
      const remaining = Math.max(0, nextStart - context.currentTime);
      playbackTimeoutRef.current = window.setTimeout(() => {
        setPlaying(false);
        stopVisualization();
        streamTimingRef.current = null;
        playbackTimeoutRef.current = null;
      }, remaining * 1000);
    } catch (reason) {
      stopAllPlayback();
      if (generationId !== null) {
        setGenerations((items) => items.filter((item) => item.id !== generationId));
      }
      setError(reason instanceof Error ? reason.message : "Speech generation failed.");
    } finally {
      generatingRef.current = false;
      setLoading(false);
    }
  }

  function stopAllPlayback() {
    const audio = audioRef.current;
    if (audio) {
      audio.pause();
      audio.currentTime = 0;
    }
    streamSourcesRef.current.forEach((source) => {
      try { source.stop(); } catch { /* The source has already ended. */ }
    });
    streamSourcesRef.current.clear();
    if (playbackTimeoutRef.current !== null) window.clearTimeout(playbackTimeoutRef.current);
    playbackTimeoutRef.current = null;
    streamTimingRef.current = null;
    stopVisualization();
    setPlaying(false);
  }

  function togglePlayback() {
    if (current && !current.url && audioContextRef.current) {
      if (playing) {
        void audioContextRef.current.suspend();
        setPlaying(false);
        stopVisualization();
      } else {
        void audioContextRef.current.resume();
        setPlaying(true);
        startVisualization(false);
      }
      return;
    }
    if (!audioRef.current) return;
    if (playing) audioRef.current.pause(); else audioRef.current.play();
  }

  function ensureAudioGraph() {
    if (!audioContextRef.current) {
      const context = new AudioContext();
      const analyser = context.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.78;
      analyser.connect(context.destination);
      audioContextRef.current = context;
      analyserRef.current = analyser;
    }
    return audioContextRef.current;
  }

  function startVisualization(connectMediaElement = true) {
    const audio = audioRef.current;
    const context = ensureAudioGraph();
    if (connectMediaElement && audio && !mediaSourceRef.current) {
      mediaSourceRef.current = context.createMediaElementSource(audio);
      mediaSourceRef.current.connect(analyserRef.current!);
    }

    void context.resume();
    if (animationRef.current !== null) cancelAnimationFrame(animationRef.current);
    const data = new Uint8Array(analyserRef.current!.frequencyBinCount);

    const draw = () => {
      analyserRef.current!.getByteFrequencyData(data);
      setLiveBars(bars.map((base, index) => {
        const bin = Math.floor((index / bars.length) * Math.min(data.length, 72));
        return Math.max(8, Math.min(76, base * .4 + data[bin] * .27));
      }));
      const timing = streamTimingRef.current;
      if (timing) {
        const elapsed = Math.max(0, Math.min(timing.duration, context.currentTime - timing.start));
        setCurrentTime(elapsed);
        setProgress(timing.duration ? elapsed / timing.duration : 0);
      }
      animationRef.current = requestAnimationFrame(draw);
    };
    draw();
  }

  function stopVisualization() {
    if (animationRef.current !== null) cancelAnimationFrame(animationRef.current);
    animationRef.current = null;
  }

  function updateTimeline() {
    const audio = audioRef.current;
    if (!audio) return;
    setCurrentTime(audio.currentTime);
    setDuration(Number.isFinite(audio.duration) ? audio.duration : 0);
    setProgress(audio.duration ? audio.currentTime / audio.duration : 0);
  }

  function seek(event: MouseEvent<HTMLDivElement>) {
    const audio = audioRef.current;
    const waveform = waveformRef.current;
    if (!audio || !waveform || !audio.duration) return;
    const bounds = waveform.getBoundingClientRect();
    const nextProgress = Math.min(1, Math.max(0, (event.clientX - bounds.left) / bounds.width));
    audio.currentTime = nextProgress * audio.duration;
    updateTimeline();
  }

  function formatTime(seconds: number) {
    if (!Number.isFinite(seconds)) return "0:00";
    return `${Math.floor(seconds / 60)}:${Math.floor(seconds % 60).toString().padStart(2, "0")}`;
  }

  return (
    <div className="app-shell">
      <aside className={`sidebar ${sidebarOpen ? "" : "sidebar-collapsed"}`}>
        <div className="brand-row">
          <div className="brand-mark"><Sparkles size={17} /></div>
          <span className="brand-name">OmniAI</span>
          <button className="icon-button collapse-button" onClick={() => setSidebarOpen(false)} aria-label="Collapse sidebar"><PanelLeftClose size={18} /></button>
        </div>
        <button className="workspace-switcher"><span className="workspace-icon">O</span><span><b>OmniAI Studio</b><small>Local workspace</small></span><ChevronsUpDown size={14} /></button>
        <button className="search-button"><Search size={16} /><span>Search</span><kbd>⌘ K</kbd></button>
        <nav>
          <p className="nav-label">Playground</p>
          <a className="nav-item active"><AudioLines size={18} /><span>Text to speech</span></a>
          <a className="nav-item disabled"><Volume2 size={18} /><span>Speech to text</span><em>Soon</em></a>
          <p className="nav-label resources-label">Workspace</p>
          <a className="nav-item disabled"><KeyRound size={18} /><span>API keys</span></a>
          <a className="nav-item disabled"><Activity size={18} /><span>Usage</span></a>
          <a className="nav-item disabled"><Gauge size={18} /><span>Models</span></a>
        </nav>
        <div className="sidebar-footer">
          <a className="nav-item"><BookOpen size={18} /><span>Documentation</span></a>
          <a className="nav-item"><CircleHelp size={18} /><span>Help & feedback</span></a>
          <div className="user-card"><div className="avatar">M</div><span><b>Personal</b><small>Developer</small></span><Settings2 size={16} /></div>
        </div>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div className="title-group">
            {!sidebarOpen && <button className="icon-button" onClick={() => setSidebarOpen(true)}><Menu size={19} /></button>}
            <div><span className="eyebrow">Playground</span><h1>Text to speech</h1></div>
          </div>
          <div className="top-actions">
            <span className="status-pill"><i /> API connected</span>
            <button className="toolbar-button" onClick={() => setHistoryOpen(true)}><Clock3 size={17} /> History</button>
            <button className="icon-button"><Moon size={18} /></button>
            <button className="icon-button" onClick={() => setSettingsOpen((value) => !value)}><Settings2 size={18} /></button>
          </div>
        </header>

        <section className="stage">
          {current ? (
            <div className="result-card">
              <div className="result-heading"><span className="result-icon"><AudioLines size={20} /></span><div><h2>Your speech is ready</h2><p>{prettyVoice(current.voice)} · Kokoro 82M</p></div></div>
              <div className={`waveform ${playing ? "is-playing" : ""}`} ref={waveformRef} onClick={seek} role="slider" aria-label="Audio position" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress * 100)}>
                {(liveBars.length ? liveBars : bars).map((height, index) => <i key={index} className={index / bars.length <= progress ? "played" : ""} style={{ height: `${height}px` }} />)}
                <span className="playhead" style={{ left: `${progress * 100}%` }} />
              </div>
              <audio ref={audioRef} src={current.url || undefined} onPlay={() => { setPlaying(true); startVisualization(); }} onPause={() => { setPlaying(false); stopVisualization(); }} onEnded={() => { setPlaying(false); stopVisualization(); updateTimeline(); }} onTimeUpdate={updateTimeline} onLoadedMetadata={updateTimeline} />
              <div className="player-row">
                <button className="play-button" onClick={togglePlayback}>{playing ? <Square size={15} fill="currentColor" /> : <Play size={17} fill="currentColor" />}</button>
                <span className="time-label">{formatTime(currentTime)} <em>/</em> {formatTime(duration)}</span>
                {current.url ? <a className="download-button" href={current.url} download={`omniai-${current.id}.wav`}><Download size={16} /> Download</a> : <span className="streaming-label"><span className="spinner" /> Streaming live</span>}
              </div>
              <p className="result-transcript">“{current.text}”</p>
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-orbit"><span><AudioLines size={28} /></span></div>
              <h2>Turn your words into speech</h2>
              <p>Choose a voice, write something below, and let Kokoro bring it to life.</p>
              <div className="example-row"><button onClick={() => setInput("Welcome to OmniAI Studio — one place to build with open models.")}>Product intro</button><button onClick={() => setInput("The quietest ideas often have the loudest impact.")}>Warm narration</button></div>
            </div>
          )}
        </section>

        <form className="composer" onSubmit={generate}>
          <textarea value={input} onChange={(event) => setInput(event.target.value)} placeholder="What would you like to hear?" maxLength={4000} />
          {error && <div className="error-message">{error}</div>}
          <div className="composer-footer"><span className="model-chip"><Sparkles size={14} /> Kokoro 82M</span><span className="character-count">{characterCount.toLocaleString()} / 4,000</span><button className="generate-button" disabled={!input.trim() || loading}>{loading ? <span className="spinner" /> : <Send size={17} />}<span>{loading ? "Generating" : "Generate speech"}</span></button></div>
        </form>
      </main>

      <aside className={`settings-panel ${settingsOpen ? "" : "settings-hidden"}`}>
        <div className="settings-header"><div><span className="eyebrow">Configuration</span><h2>Voice settings</h2></div><button className="icon-button" onClick={() => setSettingsOpen(false)}><X size={18} /></button></div>
        <div className="setting-group"><label>Model</label><button className="select-like"><span><Sparkles size={15} /><span><b>Kokoro 82M</b><small>Text to speech</small></span></span><ChevronDown size={16} /></button></div>
        <div className="setting-group"><label htmlFor="voice">Voice</label><div className="select-wrapper"><select id="voice" value={voice} onChange={(event) => setVoice(event.target.value)}>{voices.map((item) => <option value={item} key={item}>{prettyVoice(item)} — {item}</option>)}</select><ChevronDown size={16} /></div><button className="preview-link" type="button"><Play size={12} fill="currentColor" /> Preview voice</button></div>
        <div className="setting-group"><div className="label-row"><label htmlFor="speed">Speed</label><output>{speed.toFixed(2)}×</output></div><input id="speed" type="range" min="0.5" max="2" step="0.05" value={speed} onChange={(event) => setSpeed(Number(event.target.value))} /><div className="range-labels"><span>0.5×</span><span>1×</span><span>2×</span></div><p className="setting-note">Speed control is ready for backend support.</p></div>
        <div className="setting-group"><label>Response format</label><div className="format-picker"><button className="selected">WAV</button><button disabled>MP3</button><button disabled>PCM</button></div></div>
        <div className="settings-tip"><Sparkles size={17} /><div><b>Natural results</b><p>Punctuation helps the model understand pauses and rhythm.</p></div></div>
        <button className="reset-button" onClick={() => { setVoice("af_heart"); setSpeed(1); }}><RotateCcw size={15} /> Reset settings</button>
      </aside>

      {historyOpen && <div className="drawer-backdrop" onClick={() => setHistoryOpen(false)}><aside className="history-drawer" onClick={(event) => event.stopPropagation()}><div className="settings-header"><div><span className="eyebrow">Recent</span><h2>Generation history</h2></div><button className="icon-button" onClick={() => setHistoryOpen(false)}><X size={18} /></button></div>{generations.length ? <div className="history-list">{generations.map((item) => <button key={item.id} onClick={() => { const audio = new Audio(item.url); audio.play(); }}><span className="history-play"><Play size={14} fill="currentColor" /></span><span><b>{item.text}</b><small>{prettyVoice(item.voice)} · {item.createdAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</small></span></button>)}</div> : <div className="history-empty"><Clock3 size={28} /><h3>No generations yet</h3><p>Your generated speech will show up here.</p></div>}</aside></div>}
    </div>
  );
}
