import { create } from "zustand";
import { AuthAPI, setToken } from "../api/client";

export const useAuth = create((set, get) => ({
  user: null,
  loading: true,
  async hydrate() {
    const token = localStorage.getItem("biospecimen.token");
    if (!token) {
      set({ user: null, loading: false });
      return;
    }
    try {
      const user = await AuthAPI.me();
      set({ user, loading: false });
    } catch {
      setToken(null);
      set({ user: null, loading: false });
    }
  },
  async login(email, password) {
    const data = await AuthAPI.login(email, password);
    setToken(data.access_token);
    set({ user: data.user });
    return data.user;
  },
  logout() {
    setToken(null);
    set({ user: null });
  },
  hasRole(...roles) {
    const user = get().user;
    if (!user) return false;
    return roles.some((r) => user.roles.includes(r));
  },
  canOperate() {
    return get().hasRole("OPERATOR", "ADMIN");
  },
  canReview() {
    return get().hasRole("REVIEWER", "ADMIN");
  },
  isAdmin() {
    return get().hasRole("ADMIN");
  },
}));
