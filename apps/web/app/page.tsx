"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "../components/providers/AuthProvider";

export default function Home() {
  const router = useRouter();
  const { user, isLoading, isAuthenticated } = useAuth();

  useEffect(() => {
    if (isLoading) return;
    if (isAuthenticated) {
      router.replace("/campaigns");
    } else {
      router.replace("/login");
    }
  }, [isAuthenticated, isLoading, router]);

  return (
    <main className="app-shell centered-shell">
      <section className="auth-panel">
        <h1>Campaign Map Forge</h1>
        {isLoading ? (
          <p className="muted-copy">Loading…</p>
        ) : user ? (
          <p className="muted-copy">
            Redirecting to <Link href="/campaigns">your campaigns</Link>…
          </p>
        ) : (
          <p className="muted-copy">
            Redirecting to <Link href="/login">sign in</Link>…
          </p>
        )}
      </section>
    </main>
  );
}
