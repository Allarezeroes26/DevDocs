"use client";
import { useState, useEffect, useRef } from 'react';
import Navbar from './components/navbar';
import { useChatStore } from './store/useChatStore';

export default function ChatPage() {
    const { messages, isLoading, sendMessage, clearChat } = useChatStore();
    const [input, setInput] = useState("");
    const messagesEndRef = useRef(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, isLoading]);

    const handleSend = (text = input) => {
        const query = typeof text === 'string' ? text : input;
        if (!query.trim()) return;
        sendMessage(query.trim());
        setInput("");
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="flex flex-col h-screen bg-gray-50 text-slate-900 font-jetbrains">
            <Navbar />
            <main className="flex-1 overflow-y-auto p-4 md:p-8 space-y-6">
                
                {/* --- EMPTY STATE / RESET VIEW --- */}
                {messages.length === 0 && !isLoading && (
                    <div className="h-full flex flex-col items-center justify-center animate-in fade-in zoom-in duration-700">
                        {/* Branding Icon */}
                        <div className="w-20 h-20 bg-gradient-to-br from-blue-600 to-blue-800 rounded-[2rem] mb-6 flex items-center justify-center text-white text-3xl shadow-2xl shadow-blue-200 border-4 border-white">
                            EB
                        </div>

                        {/* Title Section */}
                        <div className="text-center mb-10">
                            <h2 className="text-4xl font-black tracking-tighter uppercase mb-2">
                                DEVDOCS <span className="text-blue-600">AGENT</span>
                            </h2>
                            <div className="flex items-center justify-center gap-3">
                                <span className="h-px w-8 bg-slate-200"></span>
                                <p className="text-slate-400 text-[10px] font-black uppercase tracking-[0.3em]">
                                    Hybrid Search Engine v1.0
                                </p>
                                <span className="h-px w-8 bg-slate-200"></span>
                            </div>
                        </div>

                        {/* Suggestion Grid - Mapped to MainEngine Interceptors */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full max-w-2xl">
                            {[
                                { t: "Who made you?", icon: "👨‍code", desc: "Developer info & socials" },
                                { t: "What can you do?", icon: "🧠", desc: "System purpose & capabilities" },
                                { t: "How are you built?", icon: "🛠️", desc: "View the Tech Stack architecture" },
                                { t: "Summarize my docs", icon: "📑", desc: "Requires PDFs in /docs folder" }
                            ].map((item) => (
                                <button
                                    key={item.t}
                                    onClick={() => handleSend(item.t)}
                                    className="p-5 bg-white border border-slate-200 rounded-3xl text-left hover:border-blue-500 hover:shadow-xl hover:-translate-y-1 transition-all group relative overflow-hidden"
                                >
                                    <div className="flex items-start gap-4">
                                        <span className="text-2xl">{item.icon.split('')[0]}</span>
                                        <div>
                                            <p className="text-sm font-black text-slate-800 group-hover:text-blue-600 transition-colors uppercase tracking-tight">
                                                {item.t}
                                            </p>
                                            <p className="text-[10px] text-slate-400 font-medium leading-tight mt-1">
                                                {item.desc}
                                            </p>
                                        </div>
                                    </div>
                                </button>
                            ))}
                        </div>

                        {/* Hardware Status Footer */}
                        <div className="mt-12 flex gap-8 text-[9px] font-bold text-slate-300 uppercase tracking-widest">
                            <div className="flex items-center gap-2">
                                <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></div>
                                LLM: Phi-4-Mini
                            </div>
                            <div className="flex items-center gap-2">
                                <div className="w-1.5 h-1.5 rounded-full bg-blue-500"></div>
                                Vector: ChromaDB
                            </div>
                        </div>
                    </div>
                )}

                {/* --- CHAT MESSAGES --- */}
                {messages.map((msg, idx) => (
                    <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-in slide-in-from-bottom-2`}>
                        <div className={`max-w-[85%] md:max-w-[70%] p-5 rounded-3xl shadow-sm border ${
                            msg.role === 'user' 
                                ? 'bg-blue-600 text-white border-blue-700 rounded-tr-none' 
                                : 'bg-white text-slate-800 border-slate-200 rounded-tl-none'
                        }`}>
                            <div className="text-sm md:text-base leading-relaxed font-medium whitespace-pre-wrap">
                                {msg.content}
                            </div>
                            
                            {/* Metadata Display for Assistant Messages */}
                            {msg.role === 'assistant' && (msg.latency || msg.sources) && (
                                <div className="mt-4 pt-3 border-t border-slate-100 flex justify-between items-center opacity-60">
                                    <span className="text-[9px] font-black uppercase tracking-tighter">
                                        {msg.sources?.length > 0 ? `Sources: ${msg.sources.join(', ')}` : 'System Knowledge'}
                                    </span>
                                    {msg.latency && <span className="text-[9px] font-bold">{msg.latency}s</span>}
                                </div>
                            )}
                        </div>
                    </div>
                ))}

                {isLoading && (
                    <div className="flex justify-start">
                        <div className="bg-white border border-slate-200 p-4 rounded-3xl rounded-tl-none shadow-sm flex items-center gap-3">
                            <div className="flex gap-1.5">
                                <span className="w-2 h-2 bg-blue-600 rounded-full animate-bounce [animation-duration:0.8s]"></span>
                                <span className="w-2 h-2 bg-blue-600 rounded-full animate-bounce [animation-delay:0.2s] [animation-duration:0.8s]"></span>
                                <span className="w-2 h-2 bg-blue-600 rounded-full animate-bounce [animation-delay:0.4s] [animation-duration:0.8s]"></span>
                            </div>
                            <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Ensemble Retrieval Active</span>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </main>

            {/* --- FOOTER / INPUT --- */}
            <footer className="p-4 bg-white border-t border-slate-100">
                <div className="max-w-4xl mx-auto flex flex-col gap-2">
                    <div className="flex justify-between items-center px-2">
                        <span className="text-[8px] font-black text-slate-300 uppercase tracking-[0.2em]">
                            End-to-End Encrypted Local Inference
                        </span>
                        <button 
                            onClick={clearChat} 
                            className="text-[9px] font-black text-slate-400 hover:text-red-500 transition-colors uppercase tracking-widest"
                        >
                            [ Purge Session ]
                        </button>
                    </div>
                    
                    <div className="relative">
                        <textarea
                            className="w-full p-5 pr-16 border-2 border-slate-100 rounded-[2rem] bg-slate-50 text-sm font-bold focus:border-blue-600 focus:bg-white focus:outline-none transition-all resize-none shadow-inner"
                            rows="2"
                            placeholder="Query the documentation library..."
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                        />
                        <button 
                            onClick={() => handleSend()}
                            disabled={isLoading || !input.trim()}
                            className="absolute right-3 bottom-4 p-3 bg-blue-600 text-white rounded-2xl disabled:bg-slate-200 hover:bg-blue-700 active:scale-90 transition-all shadow-lg shadow-blue-100"
                        >
                           <svg viewBox="0 0 24 24" className="w-5 h-5 fill-current"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" /></svg>
                        </button>
                    </div>
                </div>
            </footer>
        </div>
    );
}