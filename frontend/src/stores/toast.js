import { create } from "zustand";

export const useToast = create((set) => ({
  items: [],
  push(message, tone = "info") {
    const id = crypto.randomUUID();
    set((s) => ({ items: [...s.items, { id, message, tone }] }));
    setTimeout(() => set((s) => ({ items: s.items.filter((i) => i.id !== id) })), 4200);
  },
  error(err) {
    const message = err?.message || String(err);
    const code = err?.code ? `${err.code}: ` : "";
    set((s) => {
      const id = crypto.randomUUID();
      setTimeout(() => set((st) => ({ items: st.items.filter((i) => i.id !== id) })), 5200);
      return { items: [...s.items, { id, message: code + message, tone: "error" }] };
    });
  },
}));
