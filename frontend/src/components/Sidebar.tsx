"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Megaphone,
  PhoneCall,
  ShoppingBag,
  CalendarClock,
  Sparkles,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { label: "Overview", href: "/", icon: LayoutDashboard },
  { label: "Campaigns", href: "/campaigns", icon: Megaphone },
  { label: "Calls", href: "/calls", icon: PhoneCall },
  { label: "Orders", href: "/orders", icon: ShoppingBag },
  { label: "Callbacks", href: "/callbacks", icon: CalendarClock },
  { label: "Simulator", href: "/simulator", icon: Sparkles },
];

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const pathname = usePathname();

  return (
    <>
      <div
        onClick={onClose}
        className={cn(
          "fixed inset-0 z-40 bg-navy-950/40 backdrop-blur-sm transition-opacity lg:hidden",
          open ? "opacity-100" : "pointer-events-none opacity-0"
        )}
      />
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-slate-200/80 bg-white transition-transform duration-200 lg:sticky lg:top-0 lg:h-screen lg:translate-x-0 shadow-sm lg:shadow-none",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-14 items-center justify-between border-b border-slate-200/80 px-5">
          <Link href="/" className="group flex items-center gap-2.5">
            <div className="relative flex h-8 w-8 items-center justify-center rounded-lg bg-navy-900 text-white shadow-sm ring-1 ring-slate-900/10 transition-all duration-200 group-hover:scale-105 group-hover:bg-navy-950 group-hover:shadow-md">
              <span className="font-serif text-lg font-bold leading-none select-none text-white tracking-tight pb-0.5">
                बा
              </span>
            </div>
            <span className="text-base font-extrabold tracking-tight text-navy-900 transition-colors group-hover:text-navy-950">
              BARTA AI
            </span>
          </Link>
          <button
            onClick={onClose}
            aria-label="Close navigation"
            className="rounded-md p-1 text-slate-400 hover:text-navy-900 lg:hidden transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <nav className="flex-1 space-y-1.5 px-3 py-4">
          {NAV.map(({ label, href, icon: Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "group relative flex items-center gap-3 rounded-lg px-3.5 py-2.5 text-sm font-bold tracking-tight transition-all duration-200 ease-out",
                  active
                    ? "bg-navy-900 text-white shadow-card translate-x-0.5 ring-1 ring-navy-900/20"
                    : "text-slate-600 hover:bg-slate-100 hover:text-navy-950 hover:translate-x-1 hover:shadow-xs active:scale-[0.98]"
                )}
              >
                <Icon
                  className={cn(
                    "h-4 w-4 shrink-0 transition-transform duration-200 group-hover:scale-110",
                    active ? "text-white" : "text-slate-400 group-hover:text-navy-900"
                  )}
                />
                <span className="flex-1 truncate">{label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-slate-200/80 px-5 py-4 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400">
          Voice agent workspace
        </div>
      </aside>
    </>
  );
}
