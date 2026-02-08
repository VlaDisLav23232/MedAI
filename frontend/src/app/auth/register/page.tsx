"use client";

import React, { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/providers/AuthProvider";
import { ROUTES } from "@/lib/constants";
import { Heart, Mail, Lock, User, UserPlus, AlertCircle } from "lucide-react";

export default function RegisterPage() {
  const { register, error, loading, clearError } = useAuth();
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    clearError();
    const ok = await register({ name, email, password });
    if (ok) router.push(ROUTES.agent);
  }

  return (
    <main className="flex items-center justify-center min-h-[calc(100vh-4rem)] px-4 py-12">
      <div className="w-full max-w-md">
        {/* Logo / header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-4">
            <Heart className="text-brand-500" size={28} />
            <span className="text-2xl font-bold gradient-text">MedAI</span>
          </div>
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">
            Create your account
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Join the MedAI clinical co-pilot platform
          </p>
        </div>

        {/* Error alert */}
        {error && (
          <div
            role="alert"
            className="flex items-center gap-2 p-3 mb-6 rounded-xl bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-sm"
          >
            <AlertCircle size={16} className="flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label
              htmlFor="register-name"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5"
            >
              Full Name
            </label>
            <div className="relative">
              <User
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
              />
              <input
                id="register-name"
                type="text"
                required
                autoComplete="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Dr. Jane Smith"
                className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-surface-dark text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
          </div>

          <div>
            <label
              htmlFor="register-email"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5"
            >
              Email
            </label>
            <div className="relative">
              <Mail
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
              />
              <input
                id="register-email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="doctor@hospital.org"
                className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-surface-dark text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
          </div>

          <div>
            <label
              htmlFor="register-password"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5"
            >
              Password
            </label>
            <div className="relative">
              <Lock
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
              />
              <input
                id="register-password"
                type="password"
                required
                autoComplete="new-password"
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-surface-dark text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-brand-500 text-white font-medium text-sm hover:bg-brand-600 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <UserPlus size={16} />
            {loading ? "Creating account…" : "Create Account"}
          </button>
        </form>

        {/* Login link */}
        <p className="text-center text-sm text-gray-500 dark:text-gray-400 mt-6">
          Already have an account?{" "}
          <Link
            href={ROUTES.login}
            className="text-brand-500 hover:underline font-medium"
          >
            Sign in
          </Link>
        </p>
      </div>
    </main>
  );
}
