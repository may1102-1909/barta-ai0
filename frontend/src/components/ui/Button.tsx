"use client";

import React from "react";
import { cn } from "@/lib/utils";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  icon?: React.ReactNode;
}

const variants: Record<Variant, string> = {
  primary: "bg-navy-900 text-white hover:bg-navy-950 shadow-subtle hover:shadow-card focus-visible:ring-navy-900/30 active:scale-[0.98]",
  secondary:
    "bg-white text-navy-900 border border-slate-200/80 hover:border-slate-300 hover:bg-slate-50 shadow-subtle hover:shadow-card focus-visible:ring-navy-900/15 active:scale-[0.98]",
  ghost: "text-slate-600 hover:text-navy-900 hover:bg-slate-100 focus-visible:ring-navy-900/15 active:scale-[0.98]",
  danger: "text-red-600 border border-red-200 hover:bg-red-50 focus-visible:ring-red-500/20 active:scale-[0.98]",
};

const sizes: Record<Size, string> = {
  sm: "h-8 px-3 text-xs gap-1.5",
  md: "h-9 px-3.5 text-xs gap-2",
  lg: "h-11 px-5 text-sm gap-2",
};

export function Button({ variant = "primary", size = "md", icon, className, children, ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-lg font-bold tracking-tight transition-all duration-150 focus:outline-none focus-visible:ring-2 disabled:cursor-not-allowed disabled:opacity-40",
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    >
      {icon}
      {children}
    </button>
  );
}

export const buttonClass = (variant: Variant = "primary", size: Size = "md", className?: string) =>
  cn(
    "inline-flex items-center justify-center rounded-lg font-bold tracking-tight transition-all duration-150",
    variants[variant],
    sizes[size],
    className
  );
