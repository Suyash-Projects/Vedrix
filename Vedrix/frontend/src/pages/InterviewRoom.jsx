import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Mic, MicOff, Video, VideoOff, Send, Timer, AlertCircle, 
  Shield, ChevronRight, Loader2, Maximize, Lock, Volume2,
  CheckCircle2, Camera, User, BarChart3, Activity,
  LayoutDashboard, Terminal, BrainCircuit, ScanEye
} from 'lucide-react';
import useAuthStore from '../store/useAuthStore';

/* ─────────────────────────────────────────────────────────────
   SUB-COMPONENT: READY CHECK WIZARD
────────────────────────────────────────────────────────────── */
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
    } catch (err) {
      alert("Hardware access (Mic & Camera) is mandatory for this assessment.");
    } finally {
      setLoading(false);
    }
  };

  const handleStart = async () => {
    try {
      const elem = document.documentElement;
      if (elem.requestFullscreen) await elem.requestFullscreen();
      onReady();
    } catch (err) {
      console.error("Fullscreen error:", err);
      onReady();
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-950 flex items-center justify-center z-[200] p-6 font-sans">
      <div className="absolute inset-0 overflow-hidden opacity-20 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-purple-600 blur-[150px] rounded-full" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-indigo-600 blur-[150px] rounded-full" />
      </div>

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-2xl w-full bg-white/5 backdrop-blur-2xl border border-white/10 rounded-[2rem] p-10 shadow-2xl relative"
      >
        <div className="flex items-center space-x-3 mb-10">
          <div className="w-10 h-10 bg-purple-600 rounded-xl flex items-center justify-center text-white">
            <BrainCircuit size={24} />
          </div>
          <span className="text-xl font-bold text-white tracking-tight">Vedrix <span className="text-purple-400 font-medium">Proctor</span></span>
        </div>

        <AnimatePresence mode="wait">
          {step === 1 ? (
            <motion.div key="step1" initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }}>
              <h1 className="text-4xl font-extrabold text-white mb-4">Hardware Validation</h1>
              <p className="text-slate-400 text-lg mb-8 leading-relaxed">
                Before entering the secure environment, we need to verify your input devices. 
                This assessment uses **Voice Analysis** and **Live Monitoring**.
              </p>
              <div className="grid grid-cols-2 gap-4 mb-10">
                <div className={`p-6 rounded-2xl border-2 transition-all ${permissions.mic ? 'bg-purple-600/20 border-purple-500 text-white' : 'bg-white/5 border-white/10 text-slate-500'}`}>
                  <Mic size={24} className="mb-3" />
                  <span className="font-bold block">Microphone</span>
                  <span className="text-xs">{permissions.mic ? 'Detected' : 'Pending...'}</span>
                </div>
                <div className={`p-6 rounded-2xl border-2 transition-all ${permissions.cam ? 'bg-purple-600/20 border-purple-500 text-white' : 'bg-white/5 border-white/10 text-slate-500'}`}>
                  <Camera size={24} className="mb-3" />
                  <span className="font-bold block">Camera</span>
                  <span className="text-xs">{permissions.cam ? 'Detected' : 'Pending...'}</span>
                </div>
              </div>
              <button onClick={checkHardware} disabled={loading} className="w-full bg-white text-slate-950 py-4 rounded-2xl font-bold text-lg hover:bg-purple-400 hover:text-white transition-all shadow-xl flex items-center justify-center space-x-2">
                {loading ? <Loader2 className="animate-spin" /> : <span>Authorize Hardware</span>}
              </button>
            </motion.div>
          ) : (
            <motion.div key="step2" initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }}>
              <h1 className="text-4xl font-extrabold text-white mb-4">System Lock Protocol</h1>
              <p className="text-slate-400 text-lg mb-8 leading-relaxed">By entering the room, you agree to the following proctoring rules:</p>
              <ul className="space-y-4 mb-10">
                {["Fullscreen mode is mandatory and will be locked.", "Microphone must remain active throughout the session.", "Artificial intelligence will monitor tab switches and minimize events.", "All responses are recorded for HR evaluation."].map((rule, i) => (
                  <li key={i} className="flex items-start text-slate-300 text-sm">
                    <CheckCircle2 size={18} className="mr-3 text-purple-500 shrink-0 mt-0.5" />
                    {rule}
                  </li>
                ))}
              </ul>
              <button onClick={handleStart} className="w-full bg-purple-600 text-white py-4 rounded-2xl font-bold text-lg hover:bg-purple-700 transition-all shadow-2xl shadow-purple-500/20 flex items-center justify-center space-x-2">
                <span>Enter Secure Session</span>
                <Maximize size={20} />
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
};

/* ─────────────────────────────────────────────────────────────
   MAIN INTERVIEW COMPONENT
────────────────────────────────────────────────────────────── */
const InterviewRoom = ({ sessionId = "test_session", onComplete }) => {
  const { user } = useAuthStore();
  const [ready, setReady] = useState(false);
  const [messages, setMessages] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [agentStatus, setAgentStatus] = useState('Standby');
  const [timeLeft, setLeftTime] = useState(1800);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [metrics, setMetrics] = useState({ accuracy: 0, clarity: 0, depth: 0, communication: 0 });
  
  const ws = useRef(null);
  const mediaRecorder = useRef(null);
  const audioChunks = useRef([]);
  const containerRef = useRef(null);

  // 1. Text-to-Speech (Browser Native)
  const speakText = (text) => {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    const voices = window.speechSynthesis.getVoices();
    utterance.voice = voices.find(v => v.lang === 'en-US' && v.name.includes('Google')) || voices[0];
    utterance.rate = 1.0;
    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    window.speechSynthesis.speak(utterance);
  };

  // 2. WebSocket Initialization
  useEffect(() => {
    if (!ready) return;

    const urlParams = new URLSearchParams(window.location.search);
    const driveId = urlParams.get('drive_id');
    const token = urlParams.get('token');

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    let socketUrl = `${protocol}://localhost:8000/api/v1/interview/ws/${sessionId}`;
    
    // Append guest parameters if present
    if (driveId && token) {
      socketUrl += `?drive_id=${driveId}&token=${token}`;
    }
    
    ws.current = new WebSocket(socketUrl);
    ws.current.onopen = () => {
      setIsConnected(true);
      setAgentStatus('Interviewer Agent: Connecting...');
    };

    ws.current.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      switch (payload.type) {
        case 'question':
          setCurrentQuestion(payload.data);
          setMessages(prev => [...prev, { role: 'assistant', content: payload.data.question }]);
          setAgentStatus('Interviewer Agent: Asking question');
          speakText(payload.data.question);
          break;
        case 'status':
          setAgentStatus(payload.data);
          break;
        case 'metrics_update':
          setMetrics(prev => ({ ...prev, ...payload.data }));
          break;
        case 'complete':
          speakText("Assessment finalized. Returning to dashboard.");
          setTimeout(() => onComplete?.(), 4000);
          break;
        case 'error':
          setAgentStatus('System Error: ' + payload.data);
          break;
      }
    };

    const timer = setInterval(() => setLeftTime(p => p > 0 ? p - 1 : 0), 1000);
    return () => {
      ws.current?.close();
      clearInterval(timer);
      window.speechSynthesis?.cancel();
    };
  }, [ready, sessionId]);

  // 3. Voice Recording (MediaRecorder)
  const startRecording = async () => {
    audioChunks.current = [];
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder.current = new MediaRecorder(stream);
      mediaRecorder.current.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.current.push(e.data); };
      mediaRecorder.current.onstop = () => {
        const audioBlob = new Blob(audioChunks.current, { type: 'audio/webm' });
        if (ws.current?.readyState === WebSocket.OPEN) {
          ws.current.send(audioBlob);
          setAgentStatus('Decision Agent: Processing vocal input...');
        }
      };
      mediaRecorder.current.start();
      setIsRecording(true);
      setAgentStatus('Listening...');
    } catch (err) { console.error("Mic error:", err); }
  };

  const stopRecording = () => {
    if (mediaRecorder.current && isRecording) {
      mediaRecorder.current.stop();
      setIsRecording(false);
      mediaRecorder.current.stream.getTracks().forEach(t => t.stop());
    }
  };

  const toggleRecording = () => {
    if (isSpeaking) return; // Don't interrupt AI
    if (isRecording) stopRecording();
    else startRecording();
  };

  if (!ready) return <ReadyCheckWizard onReady={() => setReady(true)} />;

  return (
    <div ref={containerRef} className="fixed inset-0 bg-[#020617] text-white flex flex-col font-sans overflow-hidden">
      
      {/* TOP NAV */}
      <div className="h-16 border-b border-white/5 bg-slate-900/50 backdrop-blur-md px-8 flex items-center justify-between z-50">
        <div className="flex items-center space-x-6">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse shadow-[0_0_10px_red]" />
            <span className="text-[10px] font-black uppercase tracking-[0.3em] text-red-500">Secure Voice Session</span>
          </div>
          <div className="h-4 w-px bg-white/10" />
          <div className="flex items-center space-x-2 text-slate-400">
            <ScanEye size={14} className="text-purple-400" />
            <span className="text-[10px] font-bold uppercase tracking-wider">AI Proctoring Active</span>
          </div>
        </div>
        <div className="flex items-center space-x-12">
          <div className="flex flex-col items-end">
            <span className="text-[8px] text-slate-500 uppercase font-bold tracking-widest mb-0.5">Remaining</span>
            <div className="flex items-center text-xl font-mono font-bold text-white tracking-tighter">
              <Timer size={16} className="mr-2 text-purple-500" />
              {Math.floor(timeLeft/60)}:{String(timeLeft%60).padStart(2,'0')}
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* LEFT BAR: ANALYTICS */}
        <div className="w-80 border-r border-white/5 bg-slate-900/30 p-8 flex flex-col space-y-8">
          <div>
            <h3 className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] mb-6 flex items-center"><BarChart3 size={12} className="mr-2" /> Live Evaluation</h3>
            <div className="space-y-6">
              {[
                { label: 'Accuracy', val: metrics.accuracy, color: 'bg-emerald-500' },
                { label: 'Clarity', val: metrics.clarity, color: 'bg-blue-500' },
                { label: 'Depth', val: metrics.depth, color: 'bg-purple-500' },
                { label: 'Comms', val: metrics.communication, color: 'bg-amber-500' }
              ].map(m => (
                <div key={m.label} className="space-y-2">
                  <div className="flex justify-between text-[10px] font-bold"><span className="text-slate-400">{m.label}</span><span className="text-white">{m.val}/10</span></div>
                  <div className="h-1 bg-white/5 rounded-full overflow-hidden">
                    <motion.div animate={{ width: `${m.val * 10}%` }} className={`h-full ${m.color}`} />
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="mt-auto pt-8 border-t border-white/5">
             <div className="p-5 bg-white/5 rounded-2xl border border-white/10">
                <div className="flex items-center text-purple-400 text-[10px] font-black uppercase tracking-widest mb-2"><Activity size={14} className="mr-2" /> Agent Status</div>
                <div className="text-slate-400 text-[10px] leading-relaxed">{agentStatus}</div>
             </div>
          </div>
        </div>

        {/* CENTER: AI CORE */}
        <div className="flex-1 relative flex flex-col items-center justify-center p-12 overflow-hidden">
           <div className="absolute inset-0 z-0 flex items-center justify-center opacity-30">
              <div className="w-[600px] h-[600px] bg-purple-600/10 blur-[150px] rounded-full animate-pulse" />
           </div>
           <div className="max-w-4xl w-full z-10 text-center space-y-16">
              <div className="relative group">
                <motion.div animate={{ scale: (isRecording || isSpeaking) ? [1, 1.05, 1] : 1 }} transition={{ duration: 2, repeat: Infinity }} className={`w-56 h-56 rounded-full mx-auto relative flex items-center justify-center p-1 bg-gradient-to-tr from-purple-600 to-indigo-400 shadow-[0_0_80px_-10px_rgba(147,51,234,0.5)]`}>
                  <div className="w-full h-full bg-[#020617] rounded-full flex items-center justify-center overflow-hidden">
                    {(isRecording || isSpeaking) ? (
                      <div className="flex items-end space-x-1 h-20">
                        {[1,2,3,4,5,6,7,8].map(i => (
                          <motion.div key={i} animate={{ height: [20, Math.random() * 60 + 20, 20] }} transition={{ duration: 0.4, repeat: Infinity, delay: i * 0.05 }} className={`w-1.5 rounded-full ${isSpeaking ? 'bg-indigo-400' : 'bg-red-400'}`} />
                        ))}
                      </div>
                    ) : (
                      <BrainCircuit size={80} className="text-purple-500/50" />
                    )}
                  </div>
                </motion.div>
                <div className="absolute -bottom-4 left-1/2 -translate-x-1/2 bg-purple-600 px-4 py-1.5 rounded-full text-[10px] font-black uppercase tracking-[0.2em] shadow-xl border border-white/20">
                  {currentQuestion?.category || 'Agentic Core'}
                </div>
              </div>
              <AnimatePresence mode="wait">
                <motion.div key={currentQuestion?.id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="bg-white/5 backdrop-blur-xl border border-white/10 p-12 rounded-[2.5rem] shadow-2xl relative">
                  <div className="absolute top-0 left-12 -translate-y-1/2 bg-slate-900 border border-white/10 px-4 py-1 rounded-lg text-[9px] font-bold text-slate-500 uppercase tracking-widest">Question 0{currentQuestion?.id || 1}</div>
                  <p className="text-3xl md:text-4xl font-semibold text-white leading-tight italic">"{currentQuestion?.question || "Interviewer is preparing the first question..."}"</p>
                </motion.div>
              </AnimatePresence>
              <div className="text-[10px] font-black text-slate-500 uppercase tracking-[0.3em]">Phase: {currentQuestion?.difficulty || 'Warmup'} Mode</div>
           </div>
        </div>

        {/* RIGHT BAR: LOG */}
        <div className="w-80 border-l border-white/5 bg-slate-900/30 p-8 flex flex-col">
           <h3 className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] mb-6 flex items-center"><Terminal size={12} className="mr-2" /> Intelligence Log</h3>
           <div className="flex-1 font-mono text-[10px] text-slate-500 overflow-y-auto space-y-4 pr-2 custom-scrollbar">
              {messages.map((m, i) => (
                <div key={i} className={`pb-4 border-b border-white/5 ${m.role === 'user' ? 'text-purple-400' : 'text-slate-400'}`}>
                  <span className="text-slate-600">[{m.role.toUpperCase()}]</span> {m.content}
                </div>
              ))}
           </div>
           <div className="mt-8">
              <div className="aspect-video bg-slate-950 rounded-2xl border border-white/10 relative overflow-hidden flex items-center justify-center">
                 <div className="absolute top-2 left-3 flex items-center space-x-2"><div className="w-1.5 h-1.5 bg-purple-500 rounded-full" /><span className="text-[8px] font-bold text-white uppercase tracking-tighter">Live Feed</span></div>
                 <User size={40} className="text-slate-800" />
                 <div className="absolute bottom-2 right-3 text-[8px] font-mono text-slate-600 underline">ENCRYPTED</div>
              </div>
           </div>
        </div>
      </div>

      {/* BOTTOM CONTROL BAR */}
      <div className="h-32 border-t border-white/5 bg-slate-900/80 backdrop-blur-2xl flex items-center justify-center px-12 z-50">
          <button 
            onClick={toggleRecording}
            disabled={isSpeaking || !isConnected}
            className={`group flex items-center justify-center w-20 h-20 rounded-full transition-all duration-500 ${
              isRecording 
              ? 'bg-red-500 scale-110 shadow-[0_0_50px_rgba(239,68,68,0.4)] border-4 border-white/20' 
              : (isSpeaking || !isConnected)
              ? 'bg-slate-800 opacity-50 cursor-not-allowed'
              : 'bg-white text-slate-950 hover:bg-purple-500 hover:text-white shadow-2xl border-4 border-white/10'
            }`}
          >
            {isRecording ? <MicOff size={32} /> : <Mic size={32} />}
            {isRecording && <motion.div initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1.2 }} exit={{ opacity: 0, scale: 0.8 }} className="absolute -inset-4 border-2 border-red-500 rounded-full animate-ping pointer-events-none" />}
          </button>
          <span className={`absolute bottom-6 left-1/2 -translate-x-1/2 text-[10px] font-black tracking-widest uppercase ${isRecording ? 'text-red-500' : 'text-slate-500'}`}>
            {isRecording ? 'Stop & Send' : isSpeaking ? 'AI Speaking...' : 'Push to Speak'}
          </span>
      </div>
    </div>
  );
};

export default InterviewRoom;
