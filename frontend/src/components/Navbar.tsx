"use client";

import React from "react";
import Link from "next/link";
import { Menu, Sparkles } from "lucide-react";
import { buttonClass } from "@/components/ui/Button";

export function Navbar({ onMenu }: { onMenu: () => void }) {
  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-slate-200/80 bg-white/80 px-4 backdrop-blur-md sm:px-6 lg:px-8">
      <div className="flex items-center gap-3">
        <button
          onClick={onMenu}
          aria-label="Open navigation"
          className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-navy-900 lg:hidden"
        >
          <Menu className="h-5 w-5" />
        </button>
      </div>

      <div className="flex items-center gap-3">
        <Link href="/simulator" className={buttonClass("primary", "sm")}>
          <Sparkles className="h-3.5 w-3.5" />
          Simulator
        </Link>
      </div>
    </header>
  );
}
