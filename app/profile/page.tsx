"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { UserButton, useUser } from "@clerk/nextjs";

type AppUser = {
  id: string;
  email: string;
  display_name: string;
  role: "player" | "scorer";
  created: boolean;
};

export default function ProfilePage() {
  const { user, isLoaded } = useUser();
  const [appUser, setAppUser] = useState<AppUser | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");

  const API_BASE =
    process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8610";

  useEffect(() => {
    if (!isLoaded || !user?.primaryEmailAddress?.emailAddress) return;

    const run = async () => {
      try {
        setError("");

        const email = user.primaryEmailAddress.emailAddress;

        const syncRes = await fetch(`${API_BASE}/users/sync`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email,
            display_name:
              user.fullName || user.username || user.firstName || "Player",
          }),
        });

        const syncData = await syncRes.json();

        if (!syncRes.ok) {
          throw new Error(syncData?.detail || "Failed to sync user");
        }

        setAppUser(syncData);
        setDisplayName(syncData.display_name || "");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      }
    };

    run();
  }, [API_BASE, isLoaded, user]);

  async function saveProfile() {
    if (!appUser) return;

    try {
      setSaving(true);
      setMsg("");
      setError("");

      const res = await fetch(`${API_BASE}/users/${appUser.id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          display_name: displayName,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data?.detail || "Failed to update profile");
      }

      setAppUser((prev) =>
        prev
          ? {
              ...prev,
              display_name: data.display_name,
            }
          : prev
      );

      setMsg("Profile updated.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="min-h-screen px-6 py-10">
      <div className="mx-auto max-w-4xl">
        <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="mb-2 text-xs font-bold uppercase tracking-[0.18em] text-slate-400">
              Profile
            </div>
            <h1 className="text-3xl font-semibold text-white">My Profile</h1>
            <p className="mt-2 text-slate-300">
              Update your display name now. Future fields can live here too.
            </p>
          </div>

          <UserButton />
        </div>

        <div className="mb-6 flex flex-wrap gap-3">
          <Link
            href="/dashboard"
            className="lp-button-secondary inline-flex items-center rounded-xl px-4 py-2.5 font-semibold"
          >
            Back to Dashboard
          </Link>
        </div>

        {error && (
          <div className="mb-6 rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-rose-200">
            {error}
          </div>
        )}

        {msg && (
          <div className="mb-6 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-emerald-200">
            {msg}
          </div>
        )}

        <section className="lp-card">
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-white">Basic Info</h2>
            <p className="mt-1 text-sm text-slate-400">
              This is the name shown across the club app.
            </p>
          </div>

          <div className="grid gap-6">
            <div className="lp-interactive-panel">
              <label className="lp-form-label">Email</label>
              <input
                className="lp-input-strong opacity-70"
                value={appUser?.email || ""}
                readOnly
              />
            </div>

            <div className="lp-interactive-panel">
              <label className="lp-form-label">Display Name</label>
              <input
                className="lp-input-strong"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Enter your display name"
              />
            </div>

            <div className="lp-interactive-panel">
              <label className="lp-form-label">Role</label>
              <input
                className="lp-input-strong opacity-70"
                value={appUser?.role || ""}
                readOnly
              />
            </div>

            <div className="lp-card-soft">
              <div className="text-sm font-semibold text-slate-200">
                Future profile fields
              </div>
              <div className="mt-2 text-sm text-slate-400">
                Later we can add avatar, phone, club membership info, visibility
                settings, player bio, and whether stats are public.
              </div>
            </div>

            <div className="lp-action-strip flex flex-wrap gap-3">
              <button
                onClick={saveProfile}
                disabled={saving || !appUser}
                className="lp-button"
              >
                {saving ? "Saving..." : "Save Profile"}
              </button>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}