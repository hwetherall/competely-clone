"use client";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { ConfidenceBadge } from "@/components/common/ConfidenceBadge";
import { ExternalLink, FileText, Search, Clock } from "lucide-react";
import type { CellData } from "@/lib/types";

interface CellModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  company: string;
  variableName: string;
  data: CellData | null;
}

export function CellModal({
  open,
  onOpenChange,
  company,
  variableName,
  data,
}: CellModalProps) {
  if (!data) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-3xl max-h-[85vh] p-0 overflow-hidden">
        <DialogHeader className="px-6 pt-6 pb-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <DialogTitle className="text-xl">
                {company} - {variableName}
              </DialogTitle>
              <div className="mt-2 flex items-center gap-3">
                <ConfidenceBadge confidence={data.confidence} />
                {data.error && (
                  <Badge variant="destructive">Error</Badge>
                )}
              </div>
            </div>
          </div>
        </DialogHeader>

        <Separator />

        <ScrollArea className="max-h-[60vh] px-6 py-4">
          {/* Concise Summary */}
          <div className="mb-6">
            <h3 className="mb-2 text-sm font-semibold text-muted-foreground uppercase tracking-wide">
              Summary
            </h3>
            <p className="text-base leading-relaxed">{data.concise}</p>
          </div>

          <Separator className="my-4" />

          {/* Comprehensive Analysis */}
          <div className="mb-6">
            <h3 className="mb-2 text-sm font-semibold text-muted-foreground uppercase tracking-wide">
              Full Analysis
            </h3>
            <div className="prose prose-sm max-w-none">
              {data.comprehensive.split("\n").map((paragraph, index) => {
                if (!paragraph.trim()) return null;
                
                // Check if it's a heading (starts with **)
                if (paragraph.startsWith("**") && paragraph.endsWith("**")) {
                  return (
                    <h4 key={index} className="mt-4 mb-2 font-semibold">
                      {paragraph.replace(/\*\*/g, "")}
                    </h4>
                  );
                }
                
                // Check for list items
                if (paragraph.trim().startsWith("- ") || paragraph.trim().startsWith("* ")) {
                  return (
                    <li key={index} className="ml-4 mb-1">
                      {paragraph.replace(/^[-*]\s*/, "")}
                    </li>
                  );
                }

                // Check for numbered items
                if (/^\d+\.\s/.test(paragraph.trim())) {
                  return (
                    <li key={index} className="ml-4 mb-1 list-decimal">
                      {paragraph.replace(/^\d+\.\s*/, "")}
                    </li>
                  );
                }

                return (
                  <p key={index} className="mb-3 leading-relaxed text-foreground/90">
                    {paragraph}
                  </p>
                );
              })}
            </div>
          </div>

          <Separator className="my-4" />

          {/* Sources */}
          {data.sources.length > 0 && (
            <div className="mb-6">
              <h3 className="mb-3 text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                Sources ({data.sources.length})
              </h3>
              <div className="space-y-2">
                {data.sources.slice(0, 10).map((source, index) => (
                  <a
                    key={index}
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-start gap-3 rounded-lg border p-3 transition-colors hover:bg-muted/50"
                  >
                    <ExternalLink className="mt-0.5 h-4 w-4 flex-shrink-0 text-muted-foreground" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium text-sm">
                        {source.title || source.url}
                      </p>
                      {source.snippet && (
                        <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                          {source.snippet}
                        </p>
                      )}
                      <p className="mt-1 truncate text-xs text-muted-foreground/70">
                        {source.domain || new URL(source.url).hostname}
                      </p>
                    </div>
                  </a>
                ))}
              </div>
            </div>
          )}

          <Separator className="my-4" />

          {/* Metadata */}
          <div>
            <h3 className="mb-3 text-sm font-semibold text-muted-foreground uppercase tracking-wide">
              Research Metadata
            </h3>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <MetadataItem
                icon={Search}
                label="Iterations"
                value={data.iterations.toString()}
              />
              <MetadataItem
                icon={FileText}
                label="Total Searches"
                value={data.total_searches.toString()}
              />
              <MetadataItem
                icon={ExternalLink}
                label="Sources"
                value={data.sources.length.toString()}
              />
              {data.timestamp && (
                <MetadataItem
                  icon={Clock}
                  label="Timestamp"
                  value={new Date(data.timestamp).toLocaleDateString()}
                />
              )}
            </div>
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}

function MetadataItem({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-2 rounded-lg bg-muted/50 p-3">
      <Icon className="h-4 w-4 text-muted-foreground" />
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="font-medium text-sm">{value}</p>
      </div>
    </div>
  );
}
