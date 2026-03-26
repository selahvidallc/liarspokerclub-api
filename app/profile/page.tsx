"use client"

import Link from "next/link"
import { useEffect, useState } from "react"
import { useUser } from "@clerk/nextjs"
import type { AppRole } from "@/lib/roles"

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8610"

type AppUser = {
  id: string
  email: string
  display_name: string
  role: AppRole
  created: boolean
}

export default function ProfilePage() {
  const { user, isLoaded } = useUser()

  const [appUser, setAppUser] = useState<AppUser | null>(null)
  const [displayName, setDisplayName] = useState("")
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")
  const [msg, setMsg] = useState("")

  useEffect(() => {
    if (!isLoaded || !user?.primaryEmailAddress?.emailAddress) return

    const run = async () => {
      try {
        setLoading(true)
        setError("")
        setMsg("")

        const email = user?.primaryEmailAddress?.emailAddress
        if (!email) {
          throw new Error("No signed-in user email found")
        }

        const syncRes = await fetch(`${API_BASE}/users/sync`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email,
            display_name:
              user.fullName || user.username || user.firstName || "Player",
          }),
        })

        const syncData = await syncRes.json()

        if (!syncRes.ok) {
          throw new Error(syncData?.detail || "Failed to load profile")
        }

        setAppUser(syncData)
        setDisplayName(syncData.display_name || "")
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error")
      } finally {
        setLoading(false)
      }
    }

    run()
  }, [isLoaded, user])

  async function saveProfile() {
    if (!appUser) return

    const trimmed = displayName.trim()
    if (!trimmed) {
      setError("Display name cannot be blank.")
      return
    }

    try {
      setSaving(true)
      setError("")
      setMsg("")

      const res = await fetch(`${API_BASE}/users/${appUser.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          display_name: trimmed,
        }),
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data?.detail || "Failed to save profile")
      }

      setAppUser((prev) =>
        prev
          ? {
              ...prev,
              display_name: data.display_name,
            }
          : prev
      )
      setDisplayName(data.display_name)
      setMsg("Profile saved.")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error")
    } finally {
      setSaving(false)
    }
  }

  return (
    <main className="mx-auto max-w-xl px-6 py-10">
      <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="mb-2 text-xs font-bold uppercase tracking-[0.18em] text-slate-400">
            Profile
          </div>
          <h1 className="text-3xl font-semibold text-white">My Profile</h1>
          <p className="mt-2 text-slate-300">
            Update your display name and review your account details.
          </p>
        </div>

        <div className="flex flex-wrap gap-3">
          <Link
            href="/dashboard"
            className="lp-button-secondary inline-flex items-center rounded-xl px-4 py-2.5 font-semibold"
          >
            Back to Dashboard
          </Link>

          <Link
            href="/admin"
            className="lp-button-secondary inline-flex items-center rounded-xl px-4 py-2.5 font-semibold"
          >
            Admin
          </Link>
        </div>
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

      <div className="lp-card">
        {loading ? (
          <div className="text-slate-400">Loading profile...</div>
        ) : (
          <>
            <div className="grid gap-5">
              <div className="lp-interactive-panel">
                <label className="lp-form-label">Display Name</label>
                <input
                  className="lp-input-strong"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="Enter display name"
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="lp-card-soft">
                  <div className="text-sm text-slate-400">Email</div>
                  <div className="mt-1 font-semibold text-white break-all">
                    {appUser?.email || "—"}
                  </div>
                </div>

                <div className="lp-card-soft">
                  <div className="text-sm text-slate-400">Role</div>
                  <div className="mt-1 font-semibold text-white">
                    {appUser?.role || "—"}
                  </div>
                </div>
              </div>
            </div>

            <div className="lp-action-strip mt-6">
              <button
                onClick={saveProfile}
                disabled={saving || loading || !appUser}
                className="lp-button"
              >
                {saving ? "Saving..." : "Save Profile"}
              </button>
            </div>
          </>
        )}
      </div>
    </main>
  )
}