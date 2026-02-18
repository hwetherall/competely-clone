"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";
import { Users, Zap, Target } from "lucide-react";

const AUDIENCE_OPTIONS = [
  { id: "board", label: "Board / Exec", desc: "Strategic and high-level", icon: Users },
  { id: "vc", label: "VC / Investor", desc: "Financials and market opportunity", icon: Target },
  { id: "product", label: "Product / Strategy", desc: "Product and positioning", icon: Target },
  { id: "general", label: "General research", desc: "Neutral landscape", icon: Users },
];

const DEPTH_OPTIONS = [
  { id: "quick", label: "Quick scan", est: "~1–2 hours" },
  { id: "standard", label: "Standard", est: "~3–4 hours" },
  { id: "deep", label: "Deep dive", est: "~5–6 hours" },
];

interface AudienceConfigProps {
  audience: string;
  depth: string;
  focusCompanies: string[];
  knownContext: string;
  onAudienceChange: (v: string) => void;
  onDepthChange: (v: string) => void;
  onFocusToggle: (company: string) => void;
  onKnownContextChange: (v: string) => void;
  companyNames: string[];
  disabled?: boolean;
}

export function AudienceConfig({
  audience,
  depth,
  focusCompanies,
  knownContext,
  onAudienceChange,
  onDepthChange,
  onFocusToggle,
  onKnownContextChange,
  companyNames,
  disabled,
}: AudienceConfigProps) {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Audience</CardTitle>
          <CardDescription>Who is this report for? Affects tone and emphasis.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2">
            {AUDIENCE_OPTIONS.map((opt) => (
              <div
                key={opt.id}
                onClick={() => !disabled && onAudienceChange(opt.id)}
                className={cn(
                  "flex items-start gap-3 rounded-lg border p-4 cursor-pointer transition-colors",
                  audience === opt.id ? "border-primary bg-primary/5" : "hover:bg-muted/50"
                )}
              >
                <opt.icon className="h-5 w-5 text-muted-foreground shrink-0 mt-0.5" />
                <div>
                  <div className="font-medium text-sm">{opt.label}</div>
                  <div className="text-xs text-muted-foreground">{opt.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5" />
            Depth
          </CardTitle>
          <CardDescription>Estimated time and research depth.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3">
            {DEPTH_OPTIONS.map((opt) => (
              <button
                key={opt.id}
                type="button"
                onClick={() => !disabled && onDepthChange(opt.id)}
                disabled={disabled}
                className={cn(
                  "rounded-lg border px-4 py-2 text-sm font-medium transition-colors",
                  depth === opt.id ? "border-primary bg-primary text-primary-foreground" : "hover:bg-muted/50"
                )}
              >
                {opt.label} ({opt.est})
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {companyNames.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Focus companies</CardTitle>
            <CardDescription>Give 2x research depth to selected companies (optional).</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-4">
              {companyNames.map((name) => (
                <label key={name} className="flex items-center gap-2 cursor-pointer">
                  <Checkbox
                    checked={focusCompanies.includes(name)}
                    onCheckedChange={() => onFocusToggle(name)}
                    disabled={disabled}
                  />
                  <span className="text-sm">{name}</span>
                </label>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Known context</CardTitle>
          <CardDescription>
            Things you already know so we don’t waste time rediscovering.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Textarea
            value={knownContext}
            onChange={(e) => onKnownContextChange(e.target.value)}
            placeholder="e.g. Amazon acquired Whole Foods in 2017; focus on recent grocery tech moves."
            rows={3}
            className="resize-y"
            disabled={disabled}
          />
        </CardContent>
      </Card>
    </div>
  );
}
