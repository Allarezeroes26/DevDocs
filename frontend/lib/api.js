// lib/api.js
const BASE_URL = process.env.NEXT_PUBLIC_API_URL;

export const devDocsApi = {
  async getStatus() {
    const res = await fetch(`${BASE_URL}/`);
    if (!res.ok) throw new Error("Backend is offline");
    return res.json();
  },

  async askQuestion(question) {
    const res = await fetch(`${BASE_URL}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    if (!res.ok) {
      const errorData = await res.json();
      throw new Error(errorData.detail || "Query failed");
    }
    return res.json();
  },

  async uploadFile(file) {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${BASE_URL}/upload`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error("Upload failed");
    return res.json();
  },

  async deleteFile(filename) {
    const res = await fetch(`${BASE_URL}/delete/${filename}`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error("Delete failed");
    return res.json();
  }
};