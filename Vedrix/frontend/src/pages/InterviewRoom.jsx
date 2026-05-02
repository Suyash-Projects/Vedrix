import React, { useState, useEffect, useRef } from 'react';
import { 
  Mic, 
  MicOff, 
  Video, 
  VideoOff, 
  Send, 
  Timer, 
  AlertCircle, 
  Shield, 
  ChevronRight,
  Loader2
} from 'lucide-react';
import useAuthStore from '../store/useAuthStore';

const InterviewRoom = ({ sessionId = "test_session", onComplete }) => {
  const { user } = useAuthStore();
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [status, setStatus] = useState('Initializing AI Interviewer...');
  const [timeLeft, setLeftTime] = useState(1800); // 30 minutes
  const [currentQuestion, setCurrentQuestion] = useState(null);
  
  const ws = useRef(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    // 1. Establish WebSocket Connection
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const socketUrl = `${protocol}://localhost:8000/api/v1/interview/ws/${sessionId}`;
    
    ws.current = new WebSocket(socketUrl);

    ws.current.onopen = () => {
      setIsConnected(true);
      setStatus('Connected. AI is reviewing your resume...');
    };

    ws.current.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      
      switch (payload.type) {
        case 'question':
          const qData = payload.data;
          setCurrentQuestion(qData);
          setMessages(prev => [...prev, { 
            role: 'assistant', 
            content: qData.question,
            category: qData.category,
            difficulty: qData.difficulty
          }]);
          setStatus('Interview in Progress');
          break;
        
        case 'status':
          setStatus(payload.data);
          break;
        
        case 'complete':
          setStatus('Interview Finished');
          setMessages(prev => [...prev, { role: 'system', content: payload.data }]);
          onComplete?.();
          break;
          
        case 'error':
          setStatus('Error: ' + payload.data);
          break;
      }
    };

    ws.current.onclose = () => {
      setIsConnected(false);
      setStatus('Disconnected');
    };

    // 2. Timer Countdown
    const timer = setInterval(() => {
      setLeftTime(prev => (prev > 0 ? prev - 1 : 0));
    }, 1000);

    return () => {
      ws.current?.close();
      clearInterval(timer);
    };
  }, [sessionId]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleSendMessage = () => {
    if (!inputText.trim() || !ws.current) return;
    
    // Add user message locally
    setMessages(prev => [...prev, { role: 'user', content: inputText }]);
    
    // Send to backend
    ws.current.send(JSON.stringify({
      type: 'answer',
      data: inputText
    }));
    
    setInputText('');
    setStatus('AI is evaluating...');
  };

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] bg-gray-50 overflow-hidden">
      {/* Header / Realism Layer */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between shadow-sm">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 bg-red-50 text-red-600 px-3 py-1 rounded-full text-xs font-bold animate-pulse border border-red-100">
            <div className="w-2 h-2 bg-red-600 rounded-full" />
            <span>LIVE RECORDING</span>
          </div>
          <div className="h-4 w-px bg-gray-200" />
          <div className="text-sm font-medium text-gray-500 flex items-center">
            <Shield size={14} className="mr-1 text-purple-600" />
            Proctoring Active
          </div>
        </div>

        <div className="flex items-center space-x-6 text-sm">
          <div className="flex items-center text-gray-700 font-mono bg-gray-100 px-4 py-2 rounded-lg border border-gray-200">
            <Timer size={16} className="mr-2 text-gray-500" />
            <span className={timeLeft < 300 ? 'text-red-600 font-bold' : ''}>
              {formatTime(timeLeft)}
            </span>
          </div>
          <button className="bg-red-500 text-white px-4 py-2 rounded-lg font-bold hover:bg-red-600 transition-colors">
            End Session
          </button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Main Conversation Area */}
        <div className="flex-1 flex flex-col p-6 overflow-y-auto space-y-6">
          <div className="max-w-4xl mx-auto w-full space-y-6">
            {messages.map((msg, idx) => (
              <div 
                key={idx} 
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`max-w-[80%] p-5 rounded-2xl shadow-sm ${
                  msg.role === 'user' 
                  ? 'bg-purple-600 text-white rounded-tr-none' 
                  : msg.role === 'system'
                  ? 'bg-amber-50 text-amber-800 border border-amber-100 text-center italic w-full'
                  : 'bg-white border border-gray-100 text-gray-800 rounded-tl-none'
                }`}>
                  {msg.role === 'assistant' && (
                    <div className="flex items-center space-x-2 mb-2 text-[10px] uppercase font-bold tracking-widest text-purple-500">
                      <span>Phase: {currentQuestion?.category || 'General'}</span>
                      <span>•</span>
                      <span>{currentQuestion?.difficulty || 'Medium'}</span>
                    </div>
                  )}
                  <p className="text-lg leading-relaxed">{msg.content}</p>
                </div>
              </div>
            ))}
            <div ref={scrollRef} />
          </div>
        </div>

        {/* Media Controls Sidebar (Placeholder for realism) */}
        <div className="w-64 bg-white border-l border-gray-200 p-6 flex flex-col space-y-8">
          <div className="space-y-4">
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest">Candidate Video</h3>
            <div className="aspect-video bg-gray-900 rounded-xl flex items-center justify-center relative group overflow-hidden">
              <span className="text-gray-600 text-xs">{user?.first_name || 'Candidate'}</span>
              <div className="absolute top-2 right-2 flex space-x-1">
                <div className="w-1.5 h-1.5 bg-green-500 rounded-full" />
              </div>
            </div>
          </div>

          <div className="space-y-3">
             <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest">Controls</h3>
             <button 
              onClick={() => setIsRecording(!isRecording)}
              className={`w-full py-3 rounded-xl flex items-center justify-center space-x-2 transition-all ${
                isRecording ? 'bg-red-50 text-red-600 border border-red-100' : 'bg-gray-50 text-gray-600 border border-gray-100 hover:bg-gray-100'
              }`}
             >
               {isRecording ? <MicOff size={18}/> : <Mic size={18}/>}
               <span className="font-medium">{isRecording ? 'Mute' : 'Unmute'}</span>
             </button>
             <button className="w-full py-3 bg-gray-50 text-gray-600 border border-gray-100 rounded-xl flex items-center justify-center space-x-2 hover:bg-gray-100">
               <Video size={18}/>
               <span className="font-medium">Camera</span>
             </button>
          </div>

          <div className="mt-auto p-4 bg-purple-50 rounded-xl border border-purple-100">
            <div className="flex items-center text-purple-700 text-xs font-bold mb-2">
              <AlertCircle size={14} className="mr-1" />
              STRICT MODE
            </div>
            <p className="text-[10px] text-purple-600 leading-tight">
              AI is monitoring eye movement and tab switches. Maintain focus.
            </p>
          </div>
        </div>
      </div>

      {/* Input Area */}
      <div className="bg-white border-t border-gray-200 p-6 shadow-2xl">
        <div className="max-w-4xl mx-auto relative">
          <input
            type="text"
            className="w-full pl-6 pr-32 py-5 bg-gray-50 border-none rounded-2xl focus:ring-2 focus:ring-purple-500 outline-none text-lg transition-all"
            placeholder={isConnected ? "Speak or type your response..." : "Connecting to server..."}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
            disabled={!isConnected}
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2 flex space-x-2">
            <div className="text-[10px] text-gray-400 font-bold self-center mr-2">
               {status}
            </div>
            <button 
              onClick={handleSendMessage}
              disabled={!isConnected || !inputText.trim()}
              className="bg-purple-600 text-white p-3 rounded-xl hover:bg-purple-700 shadow-lg shadow-purple-500/30 active:scale-95 transition-all disabled:opacity-50"
            >
              <Send size={20} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InterviewRoom;
