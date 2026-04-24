"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, Loader2, Search } from "lucide-react";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useCreateDiscovery } from "@/lib/api";
import type { DiscoveryFraming, DiscoveryTargetProfile } from "@/lib/types";

const INNOVERA_PROFILE =
  "Innovera is an AI-native decision intelligence platform. Its core premise is that AI and fast-moving markets expand options faster than leadership can judge them. Innovera builds digital twins of initiatives through specialized agents covering opportunity validation, market research, competitive analysis, product and technology, GTM, financials, talent, legal, and IP. The platform combines AI analysis with expert-in-the-loop validation, sells into corporate innovators, strategy teams, and executives, and substitutes for large consulting-team engagements delivered faster.";

const DEFAULT_TARGET: DiscoveryTargetProfile = {
  company_name: "Innovera",
  website: "",
  industry: "AI-native decision intelligence",
  audience: "Corporate innovators, strategy teams, and executives",
  description: INNOVERA_PROFILE,
  notes: "",
};

const DEFAULT_FRAMING_SEEDS: Record<DiscoveryFraming, string> = {
  direct:
    "Other AI-native decision intelligence, strategy, market research, competitive analysis, or initiative digital-twin platforms.",
  problem_sharer:
    "Consulting firms and expert networks solving strategic decisions under uncertainty, including blended AI plus human models such as McKinsey QuantumBlack, BCG X, Bain Vector, Accenture, GLG, and Third Bridge.",
  category_sharer:
    "Multi-agent AI research, enterprise knowledge, analyst, and market-intelligence platforms with adjacent solution shapes, such as Glean, Hebbia, Rogo, AlphaSense, and AI analyst tools.",
  adjacency:
    "Big 4 firms, foundation-model labs, CRMs/ERPs, Palantir-like decision layers, sovereign funds, and trading houses with data, capital, or distribution that could enter decision intelligence.",
};

const FRAMING_LABELS: Record<DiscoveryFraming, string> = {
  direct: "Direct",
  problem_sharer: "Problem-Sharer",
  category_sharer: "Category-Sharer",
  adjacency: "Adjacency",
};

const FRAMING_ORDER: DiscoveryFraming[] = [
  "direct",
  "problem_sharer",
  "category_sharer",
  "adjacency",
];

export default function NewDiscoveryPage() {
  const router = useRouter();
  const createDiscovery = useCreateDiscovery();
  const [target, setTarget] = useState<DiscoveryTargetProfile>(DEFAULT_TARGET);
  const [framingSeeds, setFramingSeeds] = useState<Record<DiscoveryFraming, string>>(DEFAULT_FRAMING_SEEDS);
  const [maxCandidates, setMaxCandidates] = useState(20);

  const updateTarget = (field: keyof DiscoveryTargetProfile, value: string) => {
    setTarget((prev) => ({ ...prev, [field]: value }));
  };

  const updateSeed = (framing: DiscoveryFraming, value: string) => {
    setFramingSeeds((prev) => ({ ...prev, [framing]: value }));
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!target.company_name.trim() || !target.description.trim()) return;

    const cleanedTarget: DiscoveryTargetProfile = {
      company_name: target.company_name.trim(),
      description: target.description.trim(),
      website: target.website?.trim() || null,
      industry: target.industry?.trim() || null,
      audience: target.audience?.trim() || null,
      notes: target.notes?.trim() || null,
    };
    const cleanedSeeds = Object.fromEntries(
      FRAMING_ORDER.map((framing) => [framing, framingSeeds[framing].trim()])
        .filter(([, value]) => value)
    );

    try {
      const result = await createDiscovery.mutateAsync({
        target_profile: cleanedTarget,
        framing_seeds: cleanedSeeds,
        max_candidates: Math.max(10, Math.min(30, maxCandidates)),
      });
      router.push(`/discovery/${result.discovery_run_id}`);
    } catch (error) {
      console.error("Failed to start discovery:", error);
    }
  };

  return (
    <>
      <Header
        title="Competitor Discovery"
        description="Find Innovera-relevant competitors before launching a research run"
      />

      <form onSubmit={handleSubmit} className="mx-auto max-w-5xl space-y-6 p-6">
        <Card>
          <CardHeader>
            <CardTitle>Target Profile</CardTitle>
            <CardDescription>
              Define the company and market lens the discovery agent should search against.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="company-name">Company</Label>
                <Input
                  id="company-name"
                  value={target.company_name}
                  onChange={(event) => updateTarget("company_name", event.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="website">Website</Label>
                <Input
                  id="website"
                  value={target.website ?? ""}
                  onChange={(event) => updateTarget("website", event.target.value)}
                  placeholder="https://..."
                />
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="industry">Industry</Label>
                <Input
                  id="industry"
                  value={target.industry ?? ""}
                  onChange={(event) => updateTarget("industry", event.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="audience">Audience</Label>
                <Input
                  id="audience"
                  value={target.audience ?? ""}
                  onChange={(event) => updateTarget("audience", event.target.value)}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={target.description}
                onChange={(event) => updateTarget("description", event.target.value)}
                rows={5}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="notes">Notes</Label>
              <Textarea
                id="notes"
                value={target.notes ?? ""}
                onChange={(event) => updateTarget("notes", event.target.value)}
                rows={3}
                placeholder="Optional constraints, exclusions, or emphasis"
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Framing Seeds</CardTitle>
            <CardDescription>
              Discovery combines multiple competitor definitions so the output is broader than direct lookalikes.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 lg:grid-cols-2">
              {FRAMING_ORDER.map((framing) => (
                <div key={framing} className="space-y-2">
                  <Label htmlFor={`seed-${framing}`}>{FRAMING_LABELS[framing]}</Label>
                  <Textarea
                    id={`seed-${framing}`}
                    value={framingSeeds[framing]}
                    onChange={(event) => updateSeed(framing, event.target.value)}
                    rows={4}
                  />
                </div>
              ))}
            </div>
            <div className="max-w-48 space-y-2">
              <Label htmlFor="max-candidates">Max Candidates</Label>
              <Input
                id="max-candidates"
                type="number"
                min={10}
                max={30}
                value={maxCandidates}
                onChange={(event) => setMaxCandidates(Number(event.target.value))}
              />
            </div>
          </CardContent>
        </Card>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <Button
            type="submit"
            size="lg"
            disabled={
              createDiscovery.isPending ||
              !target.company_name.trim() ||
              !target.description.trim()
            }
          >
            {createDiscovery.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Starting...
              </>
            ) : (
              <>
                <Search className="h-4 w-4" />
                Start Discovery
              </>
            )}
          </Button>
          {createDiscovery.isError && (
            <p className="flex items-center gap-2 text-sm text-destructive">
              <AlertCircle className="h-4 w-4 shrink-0" />
              {createDiscovery.error instanceof Error
                ? createDiscovery.error.message
                : "Discovery could not be started."}
            </p>
          )}
        </div>
      </form>
    </>
  );
}
