"use client";

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";
import { BookOpenIcon, ChevronDownIcon } from "lucide-react";
import type { ComponentProps } from "react";

export type SourcesProps = ComponentProps<"div">;

export const Sources = ({ className, ...props }: SourcesProps) => (
  <Collapsible className={cn("not-prose text-xs", className)} {...props} />
);

export type SourcesTriggerProps = ComponentProps<typeof CollapsibleTrigger> & {
  count: number;
};

export const SourcesTrigger = ({
  className,
  count,
  children,
  ...props
}: SourcesTriggerProps) => (
  <CollapsibleTrigger
    className={cn(
      "flex items-center gap-1.5 text-[var(--text-subtle)] hover:text-[var(--text-muted)] transition-colors",
      className,
    )}
    {...props}
  >
    {children ?? (
      <>
        <BookOpenIcon className="h-3 w-3 text-[var(--gold)]" />
        <span className="font-medium">
          {count} source{count > 1 ? "s" : ""} consultée{count > 1 ? "s" : ""}
        </span>
        <ChevronDownIcon className="h-3 w-3" />
      </>
    )}
  </CollapsibleTrigger>
);

export type SourcesContentProps = ComponentProps<typeof CollapsibleContent>;

export const SourcesContent = ({
  className,
  ...props
}: SourcesContentProps) => (
  <CollapsibleContent
    className={cn("mt-2 flex flex-col gap-2", className)}
    {...props}
  />
);

export type SourceProps = ComponentProps<"div">;

export const Source = ({ className, children, ...props }: SourceProps) => (
  <div className={cn("flex items-start gap-2", className)} {...props}>
    {children}
  </div>
);
