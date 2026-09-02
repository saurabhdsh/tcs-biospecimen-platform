import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Navigate } from "react-router-dom";
import { PlatformAPI } from "../api/client";
import { Button, Card, Input, PageHeader, Select, StatusBadge } from "../components/ui/primitives";
import { useAuth } from "../stores/auth";
import { useToast } from "../stores/toast";

const ROLE_OPTIONS = ["OPERATOR", "REVIEWER", "ADMIN"];

export default function AdminPage() {
  const admin = useAuth((s) => s.isAdmin());
  const current = useAuth((s) => s.user);
  const toast = useToast();
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["users"], queryFn: PlatformAPI.users, enabled: admin });
  const [form, setForm] = useState({ full_name: "", email: "", password: "", roles: "OPERATOR" });

  const create = useMutation({
    mutationFn: () =>
      PlatformAPI.createUser({
        full_name: form.full_name,
        email: form.email,
        password: form.password,
        roles: [form.roles],
      }),
    onSuccess: (u) => {
      qc.invalidateQueries({ queryKey: ["users"] });
      setForm({ full_name: "", email: "", password: "", roles: "OPERATOR" });
      toast.push(`Created ${u.email}`);
    },
    onError: (e) => toast.error(e),
  });

  const remove = useMutation({
    mutationFn: (id) => PlatformAPI.deleteUser(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      toast.push("User removed");
    },
    onError: (e) => toast.error(e),
  });

  if (!admin) return <Navigate to="/" replace />;

  return (
    <div>
      <PageHeader
        kicker="Administration"
        title="Users and roles"
        description="Create platform accounts, assign operational roles, and remove users who should no longer have access."
      />
      <Card className="mb-4 p-5">
        <div className="mb-3 text-sm font-semibold text-ink-900">Create user</div>
        <form
          className="grid gap-3 md:grid-cols-2 xl:grid-cols-5"
          onSubmit={(e) => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <label className="text-sm">
            <span className="mb-1 block text-slate-600">Full name</span>
            <Input
              value={form.full_name}
              onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))}
              required
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-slate-600">Email</span>
            <Input
              type="email"
              value={form.email}
              onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
              required
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-slate-600">Password</span>
            <Input
              type="password"
              value={form.password}
              onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
              minLength={8}
              required
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-slate-600">Role</span>
            <Select value={form.roles} onChange={(e) => setForm((f) => ({ ...f, roles: e.target.value }))}>
              {ROLE_OPTIONS.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </Select>
          </label>
          <div className="flex items-end">
            <Button className="w-full justify-center" disabled={create.isPending}>
              {create.isPending ? "Creating…" : "Create user"}
            </Button>
          </div>
        </form>
      </Card>
      <Card>
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-[11px] uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">Name</th>
              <th>Email</th>
              <th>Roles</th>
              <th>Status</th>
              <th className="pr-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {(data || []).map((u) => (
              <tr key={u.id} className="border-t border-slate-100">
                <td className="px-4 py-3 font-medium">{u.full_name}</td>
                <td>{u.email}</td>
                <td>{(u.roles || []).join(", ")}</td>
                <td>
                  <StatusBadge status={u.is_active ? "ACTIVE" : "INACTIVE"} />
                </td>
                <td className="pr-4 text-right">
                  <Button
                    variant="danger"
                    disabled={remove.isPending || u.id === current?.id}
                    onClick={() => {
                      if (window.confirm(`Delete ${u.email}? They will no longer be able to sign in.`)) {
                        remove.mutate(u.id);
                      }
                    }}
                  >
                    Delete
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
