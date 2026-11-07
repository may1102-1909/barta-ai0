import React from "react";
import { User } from "lucide-react";
import type { TranscriptTurn } from "@/lib/types";
import { cn } from "@/lib/utils";

export function TranscriptThread({
  turns,
  contactName,
  className,
  dense,
}: {
  turns: TranscriptTurn[];
  contactName?: string;
  className?: string;
  dense?: boolean;
}) {
  if (turns.length === 0) {
    return <p className="text-xs italic text-slate-400">No dialogue recorded.</p>;
  }

  return (
    <div className={cn("space-y-3", className)}>
      {turns.map((turn, idx) => {
        const isAgent = turn.speaker === "agent";
        return (
          <div key={idx} className={cn("flex gap-2.5 text-xs", isAgent ? "justify-start" : "justify-end")}>
            {isAgent && (
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-navy-900 text-[10px] font-bold text-white">
                AI
              </div>
            )}
            <div
              className={cn(
                "max-w-[80%] rounded-2xl px-3.5 py-2.5",
                isAgent
                  ? "rounded-tl-sm border border-slate-200/80 bg-white text-navy-900"
                  : "rounded-tr-sm bg-navy-900 text-white"
              )}
            >
              <div className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider opacity-60">
                {isAgent ? "Agent" : contactName || "Customer"}
              </div>
              <p className={cn("leading-relaxed", dense ? "text-xs" : "text-[13px]")}>{turn.text}</p>
            </div>
            {!isAgent && (
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-slate-200/80 bg-white text-navy-900">
                <User className="h-3.5 w-3.5" />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
