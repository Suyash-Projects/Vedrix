import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Mic, MicOff, Video, VideoOff, Send, Loader2, Maximize,
  CheckCircle2, Camera, User, PhoneOff, BrainCircuit, SignalHigh,
  Play, Terminal
} from 'lucide-react';
import useAuthStore from '../store/useAuthStore';
import apiClient from '../services/api';
import Editor from '@monaco-editor/react';

/* ── WAVEFORM HEIGHTS — pre-generated for stability ────────────────────── */
const waveformHeights = Array.from({ length: 60 }, () => Math.random() * 50 + 10);

/* ── READY CHECK WIZARD ─────────────────────────────────────────────────── */
const ReadyCheckWizard = ({ onReady }) => {
  const [step, setStep] = useState(1);
  const [permissions, setPermissions] = useState({ mic: false, cam: false });
  const [loading, setLoading] = useState(false);

  const checkHardware = async () => {
    setLoading(true);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: true });
      setPermissions({ mic: true, cam: true });
      stream.getTracks().forEach(track => track.stop());
      setStep(2);
    } catch {
      alert('Hardware access (Mic & Camera) is mandatory for this assessment.');
    } finally {
      setLoading(false);
    }
  };

  const handleStart = async () => {
    try {
      if (document.documentElement.requestFullscreen) {
        await document.documentElement.requestFullscreen();
      }
    } finally {
      onReady();
    }
  };

  return (
    <div className="fixed inset-0 bg-[#020617] flex items-center justify-center z-[200] p-6 font-sans">
      <div className="absolute inset-0 overflow-hidden opacity-20 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-purple-600 blur-[150px] rounded-full" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-indigo-600 blur-[150px] rounded-full" />
      </div>

      <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
        className="max-w-2xl w-full bg-white/5 backdrop-blur-3xl border border-white/10 rounded-[3rem] p-12 shadow-2xl relative">
        <div className="flex items-center space-x-3 mb-10">
          <div className="w-10 h-10 bg-purple-600 rounded-xl flex items-center justify-center text-white">
            <BrainCircuit size={24} />
          </div>
          <span className="text-xl font-black text-white tracking-tight">Vedrix <span className="text-purple-400">Proctor</span></span>
        </div>

        <AnimatePresence mode="wait">
          {step === 1 ? (
            <motion.div key="step1" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
              <h1 className="text-5xl font-black text-white mb-6 leading-tight tracking-tighter">Hardware <br />Validation</h1>
              <p className="text-slate-400 text-lg mb-10 leading-relaxed font-medium">
                We will quickly check your microphone and camera so the interview can run smoothly.
              </p>
              <div className="grid grid-cols-2 gap-4 mb-10">
                <div className={`p-8 rounded-3xl border-2 transition-all ${permissions.mic ? 'bg-purple-600 border-purple-400 text-white' : 'bg-white/5 border-white/10 text-slate-500'}`}>
                  <Mic size={32} className="mb-4" />
                  <span className="font-black text-xs uppercase tracking-widest block">Microphone</span>
                  <span className="text-xs font-bold opacity-60 uppercase">{permissions.mic ? 'READY' : 'CHECK REQUIRED'}</span>
                </div>
                <div className={`p-8 rounded-3xl border-2 transition-all ${permissions.cam ? 'bg-purple-600 border-purple-400 text-white' : 'bg-white/5 border-white/10 text-slate-500'}`}>
                  <Camera size={32} className="mb-4" />
                  <span className="font-black text-xs uppercase tracking-widest block">Camera</span>
                  <span className="text-xs font-bold opacity-60 uppercase">{permissions.cam ? 'READY' : 'CHECK REQUIRED'}</span>
                </div>
              </div>
              <button onClick={checkHardware} disabled={loading}
                className="w-full bg-white text-slate-950 py-5 rounded-2xl font-black uppercase tracking-widest text-sm hover:bg-purple-400 hover:text-white transition-all shadow-xl flex items-center justify-center">
                {loading ? <Loader2 className="animate-spin" size={20} /> : <span>Start Validation</span>}
              </button>
            </motion.div>
          ) : (
            <motion.div key="step2" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
              <h1 className="text-5xl font-black text-white mb-6 leading-tight tracking-tighter">Pre-Interview <br />Checklist</h1>
              <p className="text-slate-400 text-lg mb-10 leading-relaxed font-medium">Before you begin, review the setup and switch to fullscreen for a focused interview experience.</p>
              <ul className="space-y-4 mb-10">
                {['Fullscreen recommended', 'Microphone and camera checked', 'Voice responses supported', 'Typed answers available when needed'].map((rule, i) => (
                  <li key={i} className="flex items-center text-slate-300 font-bold uppercase tracking-widest text-[10px]">
                    <CheckCircle2 size={16} className="mr-3 text-purple-500 shrink-0" />{rule}
                  </li>
                ))}
              </ul>
              <button onClick={handleStart}
                className="w-full bg-purple-600 text-white py-5 rounded-2xl font-black uppercase tracking-widest text-sm hover:bg-purple-500 transition-all shadow-[0_0_50px_rgba(147,51,234,0.4)] flex items-center justify-center space-x-3">
                <span>Begin Interview</span>
                <Maximize size={20} />
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
};

/* ── WAVEFORM — stable random heights, no re-render jitter ─────────────── */
const Waveform = ({ isRecording }) => {
  return (
    <div className="h-24 flex items-center justify-center space-x-1 overflow-hidden">
      {waveformHeights.map((h, i) => (
        <motion.div
          key={i}
          animate={{ height: isRecording ? h : 4, opacity: isRecording ? 1 : 0.2 }}
          transition={{ duration: 0.4, delay: i * 0.01 }}
          className="w-1 bg-purple-500 rounded-full"
        />
      ))}
    </div>
  );
};

/* ── MAIN INTERVIEW ROOM ────────────────────────────────────────────────── */
const InterviewRoom = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [resolvedSessionId] = useState(() =>
    `session_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
  );

  const [ready, setReady] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [agentStatus, setAgentStatus] = useState('Initializing...');
  const [timeLeft, setTimeLeft] = useState(0); // Overall session timer
  const [voiceAvailable, setVoiceAvailable] = useState(false);
  const [questionTimeLeft, setQuestionTimeLeft] = useState(0); // Per-question countdown

  // Auto-submit and timeout handling
  // eslint-disable-next-line react-hooks/purity
  const lastUserActivityRef = useRef(Date.now());
  const [showTimeoutConfirm, setShowTimeoutConfirm] = useState(false);
  const noResponseTimerRef = useRef(null);

  // ... (rest of states)

  const [currentQuestion, setCurrentQuestion] = useState(null);
  
  // Keep refs in sync with state for useEffect closures
  useEffect(() => {
    isRecordingRef.current = isRecording;
  }, [isRecording]);

  useEffect(() => {
    let qTimer;
    if (currentQuestion?.time_limit) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setQuestionTimeLeft(currentQuestion.time_limit);
      qTimer = setInterval(() => {
        setQuestionTimeLeft(prev => {
          if (prev <= 1) {
            clearInterval(qTimer);
            if (isRecordingRef.current) {
              // Auto-submit when timer hits zero
              toggleRecordingRef.current?.();
              setAgentStatus('Time up! Auto-submitting response...');
            }
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(qTimer);
  }, [currentQuestion]);
  const [jobRole, setJobRole] = useState('AI Interview');
  const [completedSessionId, setCompletedSessionId] = useState(null);
  const [showTextInput, setShowTextInput] = useState(false);
  const [manualText, setManualText] = useState('');
  const [codeResult, setCodeResult] = useState(null);
  
  // Coding State
  const [code, setCode] = useState("# Write your solution here...\n");
  const [isCodingMode, setIsCodingMode] = useState(false);
  const [codeLanguage, setCodeLanguage] = useState("python");

  // Video state
  const [isVideoOn, setIsVideoOn] = useState(true);
  const [videoStream, setVideoStream] = useState(null);
  const videoRef = useRef(null);

  // Attach video stream to video element
  useEffect(() => {
    if (videoRef.current && videoStream) {
      videoRef.current.srcObject = videoStream;
    }
  }, [videoStream]);

  // Initialize video on mount
  useEffect(() => {
    let localStream = null;
    const initVideo = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        localStream = stream;
        setVideoStream(stream);
      } catch {
        console.log('Camera not available, continuing without video');
        setIsVideoOn(false);
      }
    };
    if (ready) initVideo();
    return () => {
      // Clean up the stream captured in this effect's closure, not from state
      if (localStream) {
        localStream.getTracks().forEach(track => track.stop());
      }
    };
  }, [ready]); // removed videoStream from deps — it caused an infinite re-render loop

  // Toggle video function
  const toggleVideo = async () => {
    if (isVideoOn) {
      // Turn off video
      if (videoStream) {
        videoStream.getTracks().forEach(track => track.stop());
      }
      setVideoStream(null);
      setIsVideoOn(false);
    } else {
      // Turn on video
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        setVideoStream(stream);
        setIsVideoOn(true);
      } catch (err) {
        console.error('Camera access failed:', err);
      }
    }
  };
  const isRecordingRef = useRef(false);
  const toggleRecordingRef = useRef(null);

  const ws = useRef(null);
  const mediaRecorder = useRef(null);
  const audioChunks = useRef([]);
  const reconnectAttempts = useRef(0);
  const reconnectTimer = useRef(null);
  const socketUrlRef = useRef('');
  const isIntentionalClose = useRef(false);

  // ── FREE TTS via Browser Web Speech API ────────────────────────────────
  const speakWithBrowserTTS = (text) => {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.95;
    utterance.pitch = 1.0;
    // Pick a good English voice if available
    const voices = window.speechSynthesis.getVoices();
    const preferred = voices.find(v =>
      (v.name.includes('Google') && v.lang.startsWith('en')) ||
      (v.name.includes('Samantha') && v.lang.startsWith('en')) ||
      (v.name.includes('Karen') && v.lang.startsWith('en'))
    );
    if (preferred) utterance.voice = preferred;
    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);
    window.speechSynthesis.speak(utterance);
  };

  // Pre-load voices (Chrome needs this async load)
  useEffect(() => {
    const load = () => window.speechSynthesis?.getVoices();
    load();
    window.speechSynthesis?.addEventListener('voiceschanged', load);
    return () => window.speechSynthesis?.removeEventListener('voiceschanged', load);
  }, []);

  const playAudio = (base64) => {
    // If no base64 audio from backend, use free browser TTS
    if (!base64) return;
    try {
      setIsSpeaking(true);
      let mime = 'audio/opus';
      try {
        const binary = atob(base64.slice(0, 12));
        const isWav = binary.charCodeAt(0) === 0x52;
        mime = isWav ? 'audio/wav' : 'audio/opus';
      } catch { mime = 'audio/opus'; }
      const audio = new Audio(`data:${mime};base64,${base64}`);
      audio.onended = () => setIsSpeaking(false);
      audio.onerror = () => {
        console.warn('Backend audio decode failed — falling back to browser TTS');
        setIsSpeaking(false);
      };
      audio.play().catch(e => {
        console.error('Audio play() failed:', e);
        setIsSpeaking(false);
      });
    } catch (e) {
      console.error('playAudio error:', e);
      setIsSpeaking(false);
    }
  };

  const connectWebSocket = (url) => {
    if (ws.current) ws.current.close();
    ws.current = new WebSocket(url);

    ws.current.onopen = () => {
      setIsConnected(true);
      reconnectAttempts.current = 0;
      setAgentStatus('Connected. Your interviewer is ready.');
    };

    ws.current.onclose = () => {
      setIsConnected(false);
      if (isIntentionalClose.current) return;
      // Exponential back-off: 1s, 2s, 4s, 8s, max 16s
      const delay = Math.min(1000 * 2 ** reconnectAttempts.current, 16000);
      reconnectAttempts.current += 1;
      setAgentStatus(`Connection lost. Reconnecting in ${delay / 1000}s...`);
      reconnectTimer.current = setTimeout(() => connectWebSocket(url), delay);
    };

    ws.current.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      if (payload.type === 'question') {
        setCurrentQuestion(payload.data);
        if (payload.job_role) setJobRole(payload.job_role);
        setIsCodingMode(payload.is_coding || false);
        if (payload.language) setCodeLanguage(payload.language);
        setAgentStatus('Question ready. We are waiting for your response.');
        if (payload.audio) {
          playAudio(payload.audio);
        } else {
          // Free browser TTS fallback — works on every device, zero cost
          const q = payload.data?.question;
          if (q) speakWithBrowserTTS(q);
        }
      } else if (payload.type === 'status') {
        setAgentStatus(payload.data);
      } else if (payload.type === 'execution_result') {
        setCodeResult(payload.data);
        setAgentStatus('Code submitted. Reviewing your solution now.');
      } else if (payload.type === 'complete') {
        setAgentStatus('Interview complete. Preparing your report.');
        const sid = payload.session_id ?? null;
        setCompletedSessionId(sid);
        isIntentionalClose.current = true;
        // Exit fullscreen on interview complete
        if (document.fullscreenElement) {
          document.exitFullscreen();
        }
        // Navigate to report for all session types — practice sessions have reports too
        setTimeout(() => {
          if (document.fullscreenElement) {
            document.exitFullscreen();
          }
          if (sid) {
            navigate(`/report/${sid}`);
          } else {
            navigate('/dashboard');
          }
        }, 2000);
      } else if (payload.type === 'error') {
        setAgentStatus(`⚠ ${payload.data}`);
      } else if (payload.type === 'metrics_update') {
        // Real-time metrics update during interview
        setAgentStatus('Metrics updated based on your response.');
        // Could display live metrics in a dedicated UI element
        console.log('Metrics update:', payload.data);
      } else if (payload.type === 'advisor_suggestion') {
        // Phase 1A: Advisor suggestion received (primarily for HR, but candidate sees status)
        // Candidate continues normally — HR decides when to close
        console.log('Advisor suggestion:', payload.data);
      }
    };
  };

  useEffect(() => {
    if (!ready) return;

    const driveId = searchParams.get('drive_id');
    const token = searchParams.get('token');
    const scheduledSessionId = searchParams.get('scheduled_session_id');

    const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
    let wsBase = apiBase;
    if (apiBase.startsWith('https://')) {
      wsBase = 'wss://' + apiBase.substring(8);
    } else if (apiBase.startsWith('http://')) {
      wsBase = 'ws://' + apiBase.substring(7);
    }
    let socketUrl = `${wsBase}/interview/ws/${resolvedSessionId}`;
    const queryParams = [];
    if (driveId && token) {
      queryParams.push(`drive_id=${driveId}`);
      queryParams.push(`token=${token}`);
    } else if (scheduledSessionId) {
      queryParams.push(`scheduled_session_id=${scheduledSessionId}`);
      const jwt = localStorage.getItem('token');
      if (jwt) queryParams.push(`auth_token=${encodeURIComponent(jwt)}`);
    } else {
      const jwt = localStorage.getItem('token');
      if (jwt) queryParams.push(`auth_token=${encodeURIComponent(jwt)}`);
    }
    if (queryParams.length > 0) socketUrl += `?${queryParams.join('&')}`;
    socketUrlRef.current = socketUrl;
    isIntentionalClose.current = false;
    connectWebSocket(socketUrl);

    const timer = setInterval(() => setTimeLeft(p => p + 1), 1000);
    return () => {
      isIntentionalClose.current = true;
      clearTimeout(reconnectTimer.current);
      ws.current?.close();
      clearInterval(timer);
    };
  }, [ready, resolvedSessionId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Check voice capability once ready
  useEffect(() => {
    if (!ready) return;
    (async () => {
      try {
        const resp = await apiClient.get('/voice/capabilities');
        setVoiceAvailable(!!resp.data?.voice_available);
      } catch {
        setVoiceAvailable(false);
      }
    })();
  }, [ready]);

  const toggleRecording = async () => {
    // Track user activity for timeout
    lastUserActivityRef.current = Date.now();
    setShowTimeoutConfirm(false);
    clearTimeout(noResponseTimerRef.current);

    if (isRecording) {
      // Stop recording - auto-submit after silence detection
      mediaRecorder.current?.stop();
      setIsRecording(false);
      mediaRecorder.current?.stream.getTracks().forEach(t => t.stop());

      // Auto-submit after short silence (1.5 seconds of no recording)
      setAgentStatus('Processing your answer...');
      setTimeout(() => {
        const blob = new Blob(audioChunks.current, { type: 'audio/webm' });
        if (ws.current?.readyState === WebSocket.OPEN && audioChunks.current.length > 0) {
          ws.current.send(blob);
          audioChunks.current = [];
          setAgentStatus('Answer submitted. Reviewing your response...');
        }
      }, 1500);
    } else {
      audioChunks.current = [];
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder.current = new MediaRecorder(stream);
        mediaRecorder.current.ondataavailable = (e) => {
          if (e.data.size > 0) audioChunks.current.push(e.data);
        };
        mediaRecorder.current.onstop = () => {
          // Audio captured - will be sent when recording stops
        };
        mediaRecorder.current.start();
        setIsRecording(true);
        setAgentStatus('Listening... Speak your answer.');
      } catch {
        alert("Microphone access failed.");
      }
    }
  };

  // Sync toggleRecording into ref after it is defined
  useEffect(() => {
    // eslint-disable-next-line react-hooks/immutability
    toggleRecordingRef.current = toggleRecording;
  });

  const handleEndInterview = useCallback(() => {
    isIntentionalClose.current = true;
    clearTimeout(reconnectTimer.current);
    ws.current?.close();
    // Exit fullscreen on interview end
    if (document.fullscreenElement) {
      document.exitFullscreen();
    }
    if (completedSessionId) {
      navigate(`/report/${completedSessionId}`);
    } else {
      navigate('/');
    }
  }, [completedSessionId, navigate]);

  // Auto-submit on text change and timeout detection
  useEffect(() => {
    const checkActivity = setInterval(() => {
      if (!isConnected || !currentQuestion) return;

      const timeSinceActivity = Date.now() - lastUserActivityRef.current;

      // After 5 seconds of no activity, show confirmation
      if (timeSinceActivity > 5000 && !showTimeoutConfirm) {
        setShowTimeoutConfirm(true);
        setAgentStatus("Are you still there? Please respond to continue the interview.");
        noResponseTimerRef.current = setTimeout(() => {
          // If no response after 5 more seconds, end interview
          setAgentStatus("No response detected. Ending interview...");
          setTimeout(() => {
            handleEndInterview();
          }, 3000);
        }, 5000);
      }
    }, 1000);

    return () => clearInterval(checkActivity);
  }, [isConnected, currentQuestion, showTimeoutConfirm, handleEndInterview]);

  // Update activity timestamp on user interactions
  const updateActivity = useCallback(() => {
    lastUserActivityRef.current = Date.now();
    if (showTimeoutConfirm) {
      setShowTimeoutConfirm(false);
      clearTimeout(noResponseTimerRef.current);
      setAgentStatus('Welcome back! Continuing interview...');
    }
  }, [showTimeoutConfirm]);

  // Add activity listeners
  useEffect(() => {
    const handleActivity = () => updateActivity();
    window.addEventListener('click', handleActivity);
    window.addEventListener('keypress', handleActivity);
    return () => {
      window.removeEventListener('click', handleActivity);
      window.removeEventListener('keypress', handleActivity);
    };
  }, [updateActivity]);

  const submitCode = () => {
    updateActivity();
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type: 'code', data: code }));
      setAgentStatus('AI Evaluator: Analyzing logic...');
    }
  };

  const submitTextAnswer = () => {
    updateActivity();
    if (manualText.trim() && ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type: 'answer', data: manualText }));
      setAgentStatus('Text answer submitted. Reviewing your response.');
      setManualText('');
      setShowTextInput(false);
    }
  };

  const formatTimer = (s) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;

  if (!ready) return <ReadyCheckWizard onReady={() => setReady(true)} />;

  return (
    <div className="fixed inset-0 bg-[#020617] text-white flex flex-col font-sans overflow-hidden">

      {/* TOP NAV */}
      <div className="h-20 border-b border-white/5 bg-[#020617]/50 backdrop-blur-xl px-12 flex items-center justify-between z-50 shrink-0">
        <div className="flex items-center space-x-12">
          <div className="text-3xl font-black tracking-tighter flex items-center">
            <div className="w-8 h-8 bg-gradient-to-tr from-purple-600 to-indigo-400 rounded-lg mr-2" />
            Vedrix
          </div>
          <div className="h-8 w-px bg-white/10" />
          <div className="space-y-0.5">
            <h2 className="text-sm font-black uppercase tracking-widest text-white">{jobRole}</h2>
            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
              {isConnected ? 'Connected' : 'Connecting...'}
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-8">
          <div className="text-right">
            <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1 flex items-center justify-end">
              Interview Session
              <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full ml-2 inline-block animate-pulse" />
            </p>
            <p className="text-xs font-bold text-white uppercase tracking-wider">Voice and typed answers supported</p>
          </div>

          <button onClick={handleEndInterview}
            className="bg-red-500/10 border border-red-500/20 text-red-500 px-6 py-3 rounded-2xl text-xs font-black uppercase tracking-widest hover:bg-red-500 hover:text-white transition-all flex items-center space-x-2">
            <PhoneOff size={16} />
            <span>End Interview</span>
          </button>

          <div className="flex items-center space-x-3 pl-6 border-l border-white/10">
            <div className="text-right">
              <p className="text-xs font-black text-white uppercase tracking-tight">{user?.first_name || 'Candidate'}</p>
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Candidate</p>
            </div>
            <div className="w-10 h-10 bg-slate-800 rounded-xl flex items-center justify-center border border-white/10">
              <User size={20} className="text-slate-500" />
            </div>
          </div>
        </div>
      </div>

      {/* MAIN STAGE */}
      <div className="flex-1 relative flex flex-col items-center justify-center p-12 overflow-hidden">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-purple-600/5 blur-[150px] rounded-full pointer-events-none" />

        <div className="absolute top-6 right-6 flex items-center space-x-2 bg-white/5 border border-white/10 px-3 py-1.5 rounded-xl">
          <SignalHigh size={14} className={isConnected ? 'text-emerald-500' : 'text-slate-500'} />
        </div>

        {/* Video Preview */}
        {isVideoOn && videoStream && (
          <div className="absolute top-20 right-6 w-32 h-24 rounded-xl overflow-hidden border-2 border-purple-500/30 z-20">
            <video
              ref={videoRef}
              autoPlay
              muted
              playsInline
              className="w-full h-full object-cover"
            />
          </div>
        )}

        <div className="relative z-10 w-full max-w-5xl flex flex-col items-center">
          
          {/* Toggle between AI Avatar and Coding Sandbox */}
          {!isCodingMode ? (
            <div className="flex flex-col items-center space-y-12">
              <div className="relative">
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[140%] h-[140%] border border-white/5 rounded-full" />
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[160%] h-[160%] border border-white/5 rounded-full opacity-50" />

                <div className="w-72 h-72 rounded-[3rem] bg-slate-900 border border-white/10 overflow-hidden relative shadow-[0_0_100px_rgba(147,51,234,0.1)]">
                  <img
                    src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&q=80&w=1000"
                    alt="Interviewer"
                    className={`w-full h-full object-cover grayscale transition-all duration-500 ${isSpeaking ? 'scale-110 opacity-100' : 'opacity-80'}`}
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-[#020617] via-transparent to-transparent" />
                  {isSpeaking && (
                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                      <div className="flex space-x-1">
                        {[1, 2, 3, 4, 5].map(i => (
                          <motion.div key={i} animate={{ height: [8, 28, 8] }}
                            transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.1 }}
                            className="w-1.5 bg-purple-500 rounded-full" />
                        ))}
                      </div>
                    </div>
                  )}
                  <div className="absolute top-4 left-4 bg-slate-900/60 backdrop-blur border border-white/10 px-3 py-1.5 rounded-xl flex items-center space-x-2">
                    <div className="w-1.5 h-1.5 bg-purple-500 rounded-full animate-pulse" />
                    <span className="text-[8px] font-black text-white uppercase tracking-[0.2em]">Interviewer</span>
                  </div>
                </div>

                <motion.div
                  key={currentQuestion?.id}
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="absolute top-1/2 left-1/2 -translate-x-1/2 translate-y-[160px] w-[560px] bg-[#020617]/60 backdrop-blur-3xl border border-purple-500/20 px-10 py-8 rounded-3xl shadow-2xl z-20 text-center"
                >
                  <p className="text-xl font-bold text-white leading-snug italic">
                    "{currentQuestion?.question || 'Initializing your assessment...'}"
                  </p>
                </motion.div>
              </div>
            </div>
          ) : (
            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} 
              className="w-full h-[500px] bg-[#0a0f1e] border border-white/10 rounded-[2.5rem] overflow-hidden shadow-2xl relative">
               <div className="h-12 bg-white/5 border-b border-white/5 px-6 flex items-center justify-between">
                 <div className="flex items-center space-x-2">
                   <Terminal size={16} className="text-purple-400" />
                   <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">Technical Sandbox / {codeLanguage}</span>
                 </div>
                 <div className="flex items-center space-x-4">
                   <p className="text-xs font-bold text-slate-500 italic">Phase: {currentQuestion?.category}</p>
                 </div>
               </div>
               <Editor
                 height="calc(100% - 48px)"
                 theme="vs-dark"
                 language={codeLanguage}
                 value={code}
                 onChange={(val) => setCode(val)}
                 options={{
                   fontSize: 14,
                   minimap: { enabled: false },
                   padding: { top: 20 },
                   scrollBeyondLastLine: false,
                   backgroundColor: 'transparent'
                 }}
               />
               <div className="absolute bottom-6 right-6 flex items-center space-x-3">
                 {codeResult && (
                   <div className={`px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest border ${
                     codeResult.status === 'Accepted' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'
                   }`}>
                     {codeResult.status} {codeResult.time ? `· ${codeResult.time}ms` : ''}
                   </div>
                 )}
                 <button 
                   onClick={submitCode}
                   className="bg-purple-600 hover:bg-purple-500 text-white px-6 py-3 rounded-xl text-xs font-black uppercase tracking-widest shadow-xl flex items-center space-x-2 transition-all active:scale-95"
                 >
                   <Play size={14} fill="currentColor" />
                   <span>Execute & Submit</span>
                 </button>
               </div>
            </motion.div>
          )}

          {/* Control bar */}
          <div className={`flex items-center space-x-6 z-30 ${isCodingMode ? 'pt-8' : 'pt-20'}`}>
            <button onClick={toggleVideo}
              className={`w-14 h-14 rounded-full flex items-center justify-center transition-all ${isVideoOn ? 'bg-white/5 border border-white/10 text-slate-400 hover:bg-white/10' : 'bg-red-500 text-white'}`}>
              {isVideoOn ? <Video size={20} /> : <VideoOff size={20} />}
            </button>
            <button onClick={toggleRecording}
              className={`w-14 h-14 rounded-full flex items-center justify-center transition-all ${isRecording ? 'bg-red-500 text-white shadow-xl shadow-red-500/30' : 'bg-white/5 border border-white/10 text-slate-400 hover:bg-white/10'}`}>
              {isRecording ? <MicOff size={20} /> : <Mic size={20} />}
            </button>
            <button onClick={handleEndInterview}
              className="w-14 h-14 bg-red-500 rounded-full flex items-center justify-center text-white shadow-xl shadow-red-500/20 hover:bg-red-600 transition-all">
              <PhoneOff size={20} />
            </button>
          </div>
        </div>
      </div>

      {/* BOTTOM RECORDING PANEL */}
      <div className="px-12 pb-10 shrink-0">
        <div className="max-w-5xl mx-auto bg-white/2 border border-white/5 rounded-[2.5rem] p-8 backdrop-blur-xl">
          <div className="flex justify-between items-center mb-6">
            <div className="flex items-center space-x-4">
              <span className="text-sm font-black uppercase tracking-widest text-white">Your Answer</span>
              <div className={`flex items-center space-x-2 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border ${voiceAvailable ? (isRecording ? 'bg-red-500/10 text-red-400 border-red-500/20' : 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20') : 'bg-gray-500/40 text-slate-300 border-gray-500/40'}`}>
                <div className={`w-1.5 h-1.5 rounded-full animate-pulse ${isRecording ? 'bg-red-400' : voiceAvailable ? 'bg-emerald-500' : 'bg-slate-300'}`} />
                <span>{voiceAvailable ? (isRecording ? 'Recording...' : 'Voice Ready') : 'Voice Unavailable'}</span>
              </div>
              {currentQuestion?.time_limit && (
                <div className={`flex items-center space-x-2 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border ${questionTimeLeft < 10 ? 'bg-red-500/10 text-red-400 border-red-500/20 animate-pulse' : 'bg-white/5 text-slate-400 border-white/10'}`}>
                   <span>Time Remaining: {questionTimeLeft}s</span>
                </div>
              )}
              <span className="text-xs text-slate-500 font-bold uppercase tracking-widest">{agentStatus}</span>
            </div>
            <div className="text-xl font-mono font-bold tracking-tight text-white opacity-60">
              {formatTimer(timeLeft)}
            </div>
          </div>

          <Waveform isRecording={isRecording} />

          <div className="flex justify-between items-center mt-6">
            <button onClick={toggleRecording}
              className={`px-8 py-4 rounded-2xl font-black uppercase tracking-widest text-xs transition-all ${isRecording ? 'bg-red-500/10 border border-red-500/20 text-red-500 hover:bg-red-500 hover:text-white' : 'bg-purple-600 text-white hover:bg-purple-500 shadow-xl shadow-purple-500/20'}`}>
              {isRecording ? 'Stop & Send' : 'Start Responding'}
            </button>

            <div className="relative flex flex-col items-end space-y-2">
              <AnimatePresence>
                {showTextInput && (
                  <motion.div initial={{ opacity: 0, y: 10, scale: 0.95 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 10, scale: 0.95 }}
                    className="absolute top-[-220px] right-0 w-96 bg-[#0a0f1e] border border-white/10 p-6 rounded-3xl shadow-2xl z-[60]">
                    <p className="text-xs font-black text-slate-400 uppercase tracking-widest mb-3">Type Your Answer</p>
                    <textarea
                      autoFocus
                      className="w-full h-32 bg-white/5 border border-white/10 rounded-2xl p-4 text-sm text-white focus:ring-2 focus:ring-purple-500 outline-none resize-none mb-4"
                      placeholder="Type your answer here..."
                      value={manualText}
                      onChange={(e) => setManualText(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          submitTextAnswer();
                        }
                      }}
                    />
                    <div className="flex justify-end space-x-3">
                      <button onClick={() => setShowTextInput(false)} className="px-4 py-2 text-[10px] font-black uppercase text-slate-500 hover:text-white transition-colors">Cancel</button>
                      <button onClick={submitTextAnswer} className="bg-purple-600 hover:bg-purple-500 text-white px-6 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest shadow-xl">Submit</button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              <button
                onClick={() => setShowTextInput(!showTextInput)}
                className="flex items-center space-x-2 text-slate-500 font-black uppercase tracking-widest text-[10px] hover:text-white transition-colors"
              >
                 <Send size={16} className="text-purple-500" />
                 <span>{showTextInput ? 'Close Text Entry' : 'Manual Text Answer'}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InterviewRoom;
