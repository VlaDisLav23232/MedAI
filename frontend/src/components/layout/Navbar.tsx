"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/shared/ThemeToggle";
import {
  Activity,
  Bot,
  Clock,
  FileSearch,
  Menu,
  X,
} from "lucide-react";

const navLinks = [
  { href: "/", label: "Home", icon: Activity },
  { href: "/agent", label: "Co-Pilot", icon: Bot },
  { href: "/case/demo", label: "Case View", icon: FileSearch },
  { href: "/timeline/PT-12345", label: "Timeline", icon: Clock },
];

export function Navbar() {
  const pathname = usePathname();
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 10);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const isLanding = pathname === "/";

  return (
    <header
      className={cn(
        "fixed top-0 left-0 right-0 z-50 transition-all duration-300",
        scrolled || !isLanding
          ? "glass-card neo-shadow"
          : "bg-transparent"
      )}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="relative w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-accent-cyan flex items-center justify-center transition-transform group-hover:scale-105">
              <Activity size={18} className="text-white" />
              <div className="absolute -inset-0.5 rounded-lg bg-gradient-to-br from-brand-500 to-accent-cyan opacity-0 group-hover:opacity-30 blur-md transition-opacity" />
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-bold tracking-tight text-gray-900 dark:text-white leading-none">
                MedAI
              </span>
              <span className="text-[10px] font-medium text-brand-500 dark:text-brand-400 leading-none mt-0.5">
                Clinical Co-Pilot
              </span>
            </div>
          </Link>

          {/* Desktop Nav */}
          <nav className="hidden md:flex items-center gap-1">
            {navLinks.map(({ href, label, icon: Icon }) => {
              const isActive =
                pathname === href ||
                (href !== "/" && pathname.startsWith(href));
              return (
                <Link
                  key={href}
                  href={href}
                  className={cn(
                    "flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200",
                    isActive
                      ? "bg-brand-50 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400"
                      : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-surface-dark-2"
                  )}
                >
                  <Icon size={16} />
                  {label}
                </Link>
              );
            })}
          </nav>

          {/* Right side */}
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <button
              className="md:hidden p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-surface-dark-2 transition"
              onClick={() => setMobileOpen(!mobileOpen)}
            >
              {mobileOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Nav */}
      {mobileOpen && (
        <div className="md:hidden glass-card border-t border-gray-200 dark:border-gray-800">
          <div className="px-4 py-3 space-y-1">
            {navLinks.map(({ href, label, icon: Icon }) => {
              const isActive =
                pathname === href ||
                (href !== "/" && pathname.startsWith(href));
              return (
                <Link
                  key={href}
                  href={href}
                  onClick={() => setMobileOpen(false)}
                  className={cn(
                    "flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium transition-all",
                    isActive
                      ? "bg-brand-50 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400"
                      : "text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-surface-dark-2"
                  )}
                >
                  <Icon size={16} />
                  {label}
                </Link>
              );
            })}
          </div>
        </div>
      )}
    </header>
  );
}
