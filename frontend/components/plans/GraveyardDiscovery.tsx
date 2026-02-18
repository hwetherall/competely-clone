"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Loader2, Skull, X, AlertCircle } from "lucide-react";
import type { GraveyardCompany } from "@/lib/types";

interface GraveyardDiscoveryProps {
  enabled: boolean;
  onToggle: (enabled: boolean) => void;
  companies: GraveyardCompany[];
  onCompaniesChange: (companies: GraveyardCompany[]) => void;
  onDiscover: () => void;
  isDiscovering: boolean;
  error?: string | null;
}

export function GraveyardDiscovery({
  enabled,
  onToggle,
  companies,
  onCompaniesChange,
  onDiscover,
  isDiscovering,
  error,
}: GraveyardDiscoveryProps) {
  const handleRemove = (name: string) => {
    onCompaniesChange(companies.filter((c) => c.name !== name));
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between rounded-lg border p-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Skull className="h-4 w-4 text-muted-foreground" />
            <Label htmlFor="graveyard-toggle" className="font-medium">
              Post-Mortem Intelligence
            </Label>
          </div>
          <p className="text-sm text-muted-foreground">
            Discover and analyze failed companies in this space to extract cautionary lessons
            and map risk overlays onto your strategic opportunities.
          </p>
        </div>
        <Switch
          id="graveyard-toggle"
          checked={enabled}
          onCheckedChange={onToggle}
        />
      </div>

      {enabled && companies.length === 0 && !isDiscovering && (
        <Button onClick={onDiscover} variant="outline" size="sm">
          <Skull className="h-4 w-4 mr-2" />
          Discover defunct companies
        </Button>
      )}

      {isDiscovering && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Searching for defunct companies in this sector...
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
          <p className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {error}
          </p>
        </div>
      )}

      {enabled && companies.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium">
            Defunct companies ({companies.length})
          </p>
          <div className="space-y-2">
            {companies.map((c) => (
              <div
                key={c.name}
                className="flex items-start justify-between rounded-lg border p-3 bg-muted/30"
              >
                <div className="flex-1 min-w-0 space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm">{c.name}</span>
                    {c.years_active && (
                      <span className="text-xs text-muted-foreground">
                        ({c.years_active})
                      </span>
                    )}
                  </div>
                  {c.peak_description && (
                    <p className="text-xs text-muted-foreground">
                      {c.peak_description}
                    </p>
                  )}
                  {c.reason_summary && (
                    <p className="text-xs text-destructive/80">
                      {c.reason_summary}
                    </p>
                  )}
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 shrink-0"
                  onClick={() => handleRemove(c.name)}
                >
                  <X className="h-3 w-3" />
                </Button>
              </div>
            ))}
          </div>
          <Button
            onClick={onDiscover}
            variant="outline"
            size="sm"
            disabled={isDiscovering}
          >
            {isDiscovering ? (
              <Loader2 className="h-4 w-4 animate-spin mr-1" />
            ) : (
              <Skull className="h-4 w-4 mr-1" />
            )}
            Re-discover
          </Button>
        </div>
      )}
    </div>
  );
}
