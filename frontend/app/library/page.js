"use client";
import { useState, useEffect } from 'react';
import { devDocsApi } from '@/lib/api';
import Navbar from '../components/navbar'; // Import here

export default function LibraryPage() {
    const [files, setFiles] = useState([]);
    const [isUploading, setIsUploading] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const [message, setMessage] = useState({ text: "", type: "" });

    useEffect(() => { fetchStatus(); }, []);

    const fetchStatus = async () => {
        try {
            const data = await devDocsApi.getStatus();
            setFiles(data.loaded_files || []);
        } catch (error) {
            setMessage({ text: "Backend is offline.", type: "error" });
        } finally {
            setIsLoading(false);
        }
    };

    const handleUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        setIsUploading(true);
        try {
            await devDocsApi.uploadFile(file);
            setMessage({ text: `${file.name} indexed!`, type: "success" });
            fetchStatus(); 
        } catch (error) {
            setMessage({ text: error.message, type: "error" });
        } finally {
            setIsUploading(false);
            e.target.value = null; 
        }
    };

    const handleDelete = async (filename) => {
        if (!confirm(`Delete ${filename}?`)) return;
        try {
            await devDocsApi.deleteFile(filename);
            fetchStatus();
        } catch (error) {
            setMessage({ text: "Delete failed.", type: "error" });
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 flex flex-col text-slate-900">
            <Navbar /> {/* Replaced local header with Component */}

            <main className="flex-1 max-w-4xl mx-auto w-full p-8">
                <div className="flex justify-between items-center mb-8">
                    <h2 className="text-2xl font-extrabold text-slate-800">Your Documents</h2>
                    <label className={`px-5 py-2.5 rounded-xl font-bold text-sm cursor-pointer transition-all shadow-md ${
                        isUploading ? 'bg-slate-200 text-slate-400' : 'bg-blue-600 text-white hover:bg-blue-700'
                    }`}>
                        {isUploading ? "Indexing..." : "Upload PDF"}
                        <input type="file" className="hidden" onChange={handleUpload} disabled={isUploading} accept=".pdf" />
                    </label>
                </div>

                {message.text && (
                    <div className={`mb-6 p-4 rounded-xl text-sm font-bold border ${
                        message.type === 'success' ? 'bg-green-50 text-green-700 border-green-200' : 'bg-red-50 text-red-700 border-red-200'
                    }`}>
                        {message.text}
                    </div>
                )}

                <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                    {isLoading ? (
                        <div className="p-20 text-center text-slate-400 italic">Scanning engine...</div>
                    ) : (
                        <table className="w-full">
                            <tbody className="divide-y divide-slate-100">
                                {files.map((file) => (
                                    <tr key={file} className="hover:bg-slate-50/80 group transition-colors">
                                        <td className="p-5 text-sm font-semibold text-slate-700 flex items-center gap-3">
                                            <span className="text-blue-500">📄</span> {file}
                                        </td>
                                        <td className="p-5 text-right">
                                            <button onClick={() => handleDelete(file)} className="text-red-500 hover:bg-red-50 px-3 py-1 rounded-lg text-xs font-bold opacity-0 group-hover:opacity-100 transition-all">
                                                Remove
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            </main>
        </div>
    );
}