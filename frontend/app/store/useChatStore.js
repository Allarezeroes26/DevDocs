import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { devDocsApi } from '@/lib/api';

export const useChatStore = create(
  persist(
    (set, get) => ({
      messages: [],
      isLoading: false, // Move loading state here

      addMessage: (msg) => set((state) => ({ 
        messages: [...state.messages, msg] 
      })),

      clearChat: () => set({ messages: [], isLoading: false }),

      // Move the logic here so it runs independently of the UI tab
      sendMessage: async (userQuery) => {
        if (get().isLoading) return;

        // 1. Add User Message
        set((state) => ({ 
          messages: [...state.messages, { role: 'user', content: userQuery }],
          isLoading: true 
        }));

        try {
            const data = await devDocsApi.askQuestion(userQuery);
            
            // 2. Add Assistant Message
            set((state) => ({
                messages: [...state.messages, { 
                    role: 'assistant', 
                    content: data.answer,
                    latency: data.latency,
                    sources: data.sources 
                }],
                isLoading: false
            }));
        } catch (error) {
            set((state) => ({
                messages: [...state.messages, { 
                    role: 'assistant', 
                    content: `⚠️ Error: ${error.message}` 
                }],
                isLoading: false
            }));
        }
      }
    }),
    { name: 'devdocs-chat-storage' }
  )
);