"use client";
import Navbar from '../components/navbar';

export default function AboutPage() {
    const sections = [
        {
            title: "Model Strengths",
            icon: "💪",
            items: [
                "Zero-latency local inference (Phi-4 Mini)",
                "High precision in technical documentation extraction",
                "Hybrid search: BM25 + Semantic Vector embeddings",
                "100% Data Privacy: Processing never leaves your RAM"
            ],
            color: "border-green-100 bg-green-50/50 text-green-900"
        },
        {
            title: "Current Limitations",
            icon: "⚠️",
            items: [
                "100MB maximum file size for stable indexing",
                "Context window limits very long logical chain reasoning",
                "Requires Poppler/Tesseract for image-based PDFs",
                "Performance is tied to local CPU/RAM hardware"
            ],
            color: "border-amber-100 bg-amber-50/50 text-amber-900"
        }
    ];

    return (
        <div className="min-h-screen bg-gray-50 flex flex-col">
            <Navbar />

            <main className="flex-1 max-w-6xl mx-auto w-full p-6 md:p-12 text-slate-800">
                <div className="flex flex-col md:flex-row gap-12">
                    
                    {/* --- ASIDE: DEV INFO & INSTRUCTIONS --- */}
                    <aside className="md:w-1/3 space-y-6">
                        <div className="bg-white p-8 rounded-3xl border border-slate-200 shadow-sm">
                            <div className="w-12 h-12 bg-blue-600 rounded-xl mb-4 flex items-center justify-center text-white font-bold">
                                EB
                            </div>
                            <h3 className="text-xl font-bold">Erwin Bacani</h3>
                            <p className="text-[10px] font-black text-blue-600 uppercase tracking-widest mb-4">Lead Developer</p>
                            <p className="text-sm text-slate-500 leading-relaxed font-medium">
                                Architecting local-first AI solutions. I focus on high-security RAG systems that run entirely on-device.
                            </p>
                        </div>

                        <div className="bg-blue-50 p-8 rounded-3xl border border-blue-100 shadow-sm">
                            <h3 className="text-sm font-black text-blue-700 uppercase tracking-widest mb-6">Instructions</h3>
                            <ul className="space-y-4">
                                {[
                                    "Upload PDFs to the Library page.",
                                    "Wait for indexing to complete.",
                                    "Query your documents in the Chat."
                                ].map((text, i) => (
                                    <li key={i} className="flex gap-3 items-start text-xs font-bold text-blue-600">
                                        <span>0{i+1}</span>
                                        <p className="text-slate-600 font-medium">{text}</p>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </aside>

                    {/* --- MAIN CONTENT --- */}
                    <div className="md:w-2/3 space-y-8">
                        <section>
                            <h2 className="text-4xl font-black tracking-tight mb-2">
                                System <span className="text-blue-600">Capabilities</span>
                            </h2>
                            <p className="text-slate-400 text-sm font-bold mb-10">Analysis of the RAG engine performance.</p>
                            
                            <div className="grid gap-6">
                                {sections.map((sec) => (
                                    <div key={sec.title} className={`p-8 rounded-3xl border-2 ${sec.color} shadow-sm`}>
                                        <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                                            {sec.icon} {sec.title}
                                        </h3>
                                        <ul className="space-y-3">
                                            {sec.items.map((item, i) => (
                                                <li key={i} className="flex items-center gap-3 text-xs font-bold">
                                                    <div className="w-1 h-1 rounded-full bg-current opacity-40"></div>
                                                    {item}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                ))}
                            </div>
                        </section>

                        {/* Updated Tech Specs to match main.py */}
                        <div className="bg-white p-8 rounded-3xl border border-slate-200 shadow-sm grid grid-cols-3 gap-4">
                            <div>
                                <p className="text-[9px] font-black text-slate-400 uppercase">Model</p>
                                <p className="text-xs font-bold text-slate-800">Phi-4 Mini</p>
                            </div>
                            <div>
                                <p className="text-[9px] font-black text-slate-400 uppercase">Embeddings</p>
                                <p className="text-xs font-bold text-slate-800">Nomic / Ollama</p>
                            </div>
                            <div>
                                <p className="text-[9px] font-black text-slate-400 uppercase">Vector DB</p>
                                <p className="text-xs font-bold text-slate-800">ChromaDB</p>
                            </div>
                        </div>
                    </div>
                </div>
            </main>

            <footer className="p-8 text-center text-[10px] text-slate-400 font-bold uppercase tracking-[0.4em]">
                Local RAG Stack • Erwin Bacani • 2026
            </footer>
        </div>
    );
}