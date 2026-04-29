"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { RunDetailV2, WhiteSpaceOpportunity, NextStepItem, RiskOverlay, CautionaryNarrative } from "@/lib/types";
import { getConfidenceColor } from "@/lib/api";

interface ResultsV2Props {
  data: RunDetailV2;
}

function byCategory(
  parameterDefinitions: RunDetailV2["parameter_definitions"],
  parameters: string[]
): Record<string, string[]> {
  const map: Record<string, string[]> = {};
  for (const pid of parameters) {
    const def = parameterDefinitions[pid];
    const cat = def?.category || "Other";
    if (!map[cat]) map[cat] = [];
    map[cat].push(pid);
  }
  return map;
}

export function ResultsV2({ data }: ResultsV2Props) {
  const [openParamId, setOpenParamId] = useState<string | null>(null);
  const { executive, analyses, parameters, parameter_definitions, metadata } = data;
  const categories = byCategory(parameter_definitions, parameters);
  const activeAnalysis = openParamId ? analyses[openParamId] : null;
  const typologyDistribution = metadata.typology_distribution as Record<string, number> | undefined;
  const coverageCheck = metadata.coverage_check as
    | { gap_count?: number; covered_checks?: number; total_checks?: number; gaps?: Array<Record<string, string>> }
    | undefined;

  return (
    <div className="space-y-8">
      {/* Venture Context Banner */}
      {executive.venture_context && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
          <p className="text-xs font-semibold text-amber-700 uppercase tracking-wide mb-1">Venture Context</p>
          <p className="text-sm text-amber-900">{executive.venture_context}</p>
        </div>
      )}

      {(typologyDistribution || coverageCheck) && (
        <Card>
          <CardHeader>
            <h2 className="text-xl font-semibold">Commercial Deep Dive</h2>
          </CardHeader>
          <CardContent className="space-y-4">
            {typologyDistribution && (
              <div>
                <h3 className="mb-2 text-sm font-semibold text-gray-700">Competitor Typology</h3>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(typologyDistribution).map(([type, count]) => (
                    <Badge key={type} variant="outline" className="capitalize">
                      {type.replace(/_/g, " ")}: {count}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
            {coverageCheck && (
              <div>
                <h3 className="mb-2 text-sm font-semibold text-gray-700">Coverage</h3>
                <p className="text-sm text-gray-600">
                  {coverageCheck.covered_checks ?? 0} of {coverageCheck.total_checks ?? 0} commercial question checks covered.
                  {coverageCheck.gap_count ? ` ${coverageCheck.gap_count} gaps surfaced.` : " No gaps surfaced."}
                </p>
                {!!coverageCheck.gaps?.length && (
                  <div className="mt-3 max-h-48 overflow-y-auto rounded-md border bg-gray-50">
                    <table className="min-w-full text-xs">
                      <thead>
                        <tr className="border-b bg-white">
                          <th className="px-3 py-2 text-left font-medium">Company</th>
                          <th className="px-3 py-2 text-left font-medium">Question</th>
                          <th className="px-3 py-2 text-left font-medium">Reason</th>
                        </tr>
                      </thead>
                      <tbody>
                        {coverageCheck.gaps.slice(0, 30).map((gap, i) => (
                          <tr key={i} className="border-b last:border-0">
                            <td className="px-3 py-2">{gap.company}</td>
                            <td className="px-3 py-2">{gap.question}</td>
                            <td className="px-3 py-2">{gap.reason}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Executive Brief */}
      <Card>
        <CardHeader>
          <h2 className="text-xl font-semibold">Executive Brief</h2>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Summary */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Summary</h3>
            <p className="text-gray-700 leading-relaxed whitespace-pre-line">
              {executive.brief || "No executive brief."}
            </p>
          </div>

          {/* Key Themes */}
          {executive.key_themes && executive.key_themes.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Key Themes</h3>
              <ul className="list-disc pl-5 text-sm text-gray-600 space-y-1">
                {executive.key_themes.map((t, i) => (
                  <li key={i}>{t}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Trends */}
          {executive.trends && executive.trends.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Trends</h3>
              <ul className="list-disc pl-5 text-sm text-gray-600 space-y-1">
                {executive.trends.map((t, i) => (
                  <li key={i}>{t}</li>
                ))}
              </ul>
            </div>
          )}

          {/* White Space - Strategic Opportunities (Option B) */}
          {executive.white_space_opportunities && executive.white_space_opportunities.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">White Space &mdash; Strategic Opportunities</h3>
              <div className="space-y-3">
                {executive.white_space_opportunities.map((opp: WhiteSpaceOpportunity, i: number) => {
                  const diffColor = opp.entry_difficulty === "Low" ? "bg-green-100 text-green-800" : opp.entry_difficulty === "High" ? "bg-red-100 text-red-800" : "bg-yellow-100 text-yellow-800";
                  const overlay = data.postmortem_brief?.risk_overlays?.find(
                    (r: RiskOverlay) => r.white_space_opportunity === opp.opportunity
                  );
                  const riskColor = overlay?.risk_level === "High" ? "bg-red-100 text-red-800 border-red-200" : overlay?.risk_level === "Low" ? "bg-green-100 text-green-800 border-green-200" : "bg-amber-100 text-amber-800 border-amber-200";
                  return (
                    <div key={i} className="border rounded-lg p-4 bg-gray-50">
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <h4 className="font-semibold text-gray-900 text-sm">{i + 1}. {opp.opportunity}</h4>
                        <div className="flex gap-1.5 shrink-0">
                          {overlay && (
                            <span className={`text-xs px-2 py-0.5 rounded border whitespace-nowrap ${riskColor}`}>
                              {overlay.risk_level} risk
                            </span>
                          )}
                          <span className={`text-xs px-2 py-0.5 rounded whitespace-nowrap ${diffColor}`}>{opp.entry_difficulty} entry</span>
                        </div>
                      </div>
                      <p className="text-sm text-gray-600 mb-1"><span className="font-medium text-gray-700">Why it exists:</span> {opp.why_it_exists}</p>
                      <p className="text-sm text-gray-600"><span className="font-medium text-gray-700">Best positioned:</span> {opp.who_is_closest}</p>
                      {overlay && overlay.historical_precedent && overlay.historical_precedent !== "No direct historical precedent identified." && (
                        <div className="mt-3 p-3 bg-slate-100 border border-slate-200 rounded-md">
                          <p className="text-xs font-medium text-slate-700 mb-1">Historical Risk</p>
                          <p className="text-xs text-slate-600">{overlay.historical_precedent}</p>
                          {overlay.mitigation_guidance && (
                            <p className="text-xs text-slate-600 mt-1"><span className="font-medium">Mitigation:</span> {overlay.mitigation_guidance}</p>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* White Space - Gap Matrix (Option C) */}
          {executive.white_space_matrix && (
            (() => {
              const matrix = executive.white_space_matrix;
              const matrixLabels: Record<string, [string, string]> = {
                segment_gaps: ["Segment Gaps", "Customer segments nobody serves well"],
                product_gaps: ["Product Gaps", "Capabilities or features nobody offers"],
                business_model_gaps: ["Business Model Gaps", "Monetization approaches nobody has tried"],
                geographic_gaps: ["Geographic Gaps", "Markets or regions nobody addresses"],
              };
              const hasAny = Object.keys(matrixLabels).some(k => (matrix as Record<string, string[] | undefined>)[k]?.length);
              if (!hasAny) return null;
              return (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">White Space &mdash; Gap Matrix</h3>
                  <div className="grid gap-3 md:grid-cols-2">
                    {Object.entries(matrixLabels).map(([key, [label, desc]]) => {
                      const items = (matrix as Record<string, string[] | undefined>)[key];
                      if (!items || items.length === 0) return null;
                      return (
                        <div key={key} className="border rounded-lg p-4 bg-gray-50">
                          <h4 className="font-semibold text-gray-800 text-sm mb-1">{label}</h4>
                          <p className="text-xs text-gray-500 mb-2">{desc}</p>
                          <ul className="list-disc pl-5 space-y-1 text-sm text-gray-600">
                            {items.map((item, i) => <li key={i}>{item}</li>)}
                          </ul>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })()
          )}

          {/* Next Steps */}
          {executive.next_steps && (
            (() => {
              const ns = executive.next_steps;
              const bucketLabels: Record<string, [string, string, string, string]> = {
                investigate_further: ["Investigate Further", "Needs deeper research before acting", "bg-blue-50 border-blue-200", "text-blue-700"],
                quick_wins: ["Quick Wins", "Low-effort, high-signal actions achievable in weeks", "bg-green-50 border-green-200", "text-green-700"],
                strategic_bets: ["Strategic Bets", "Bigger moves with outsized payoff", "bg-purple-50 border-purple-200", "text-purple-700"],
                monitor_and_defend: ["Monitor & Defend", "Competitive moves to watch", "bg-orange-50 border-orange-200", "text-orange-700"],
              };
              const hasAny = Object.keys(bucketLabels).some(k => (ns as Record<string, NextStepItem[] | undefined>)[k]?.length);
              if (!hasAny) return null;
              return (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">Next Steps</h3>
                  <div className="space-y-4">
                    {Object.entries(bucketLabels).map(([key, [label, desc, bgClass, textClass]]) => {
                      const items = (ns as Record<string, NextStepItem[] | undefined>)[key];
                      if (!items || items.length === 0) return null;
                      return (
                        <div key={key} className={`border ${bgClass} rounded-lg p-4`}>
                          <h4 className={`font-semibold ${textClass} text-sm mb-1`}>{label}</h4>
                          <p className="text-xs text-gray-500 mb-3">{desc}</p>
                          <div className="space-y-2">
                            {items.map((item: NextStepItem, i: number) => {
                              const priColor = item.priority === "High" ? "bg-red-100 text-red-800" : item.priority === "Low" ? "bg-gray-100 text-gray-800" : "bg-yellow-100 text-yellow-800";
                              return (
                                <div key={i} className="bg-white rounded p-3 border border-gray-100">
                                  <div className="flex items-start justify-between gap-2 mb-1">
                                    <p className="text-sm font-medium text-gray-900">{item.action}</p>
                                    <span className={`text-xs px-2 py-0.5 rounded whitespace-nowrap ${priColor}`}>{item.priority}</span>
                                  </div>
                                  <p className="text-xs text-gray-500">{item.rationale}</p>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })()
          )}
        </CardContent>
      </Card>

      {/* Post-Mortem Intelligence */}
      {data.postmortem_brief && data.postmortem_brief.failure_patterns?.length > 0 && (
        <Card className="border-l-4 border-l-slate-500">
          <CardHeader>
            <h2 className="text-xl font-semibold text-slate-800">Post-Mortem Intelligence</h2>
            <p className="text-sm text-muted-foreground">
              Lessons from {data.graveyard_companies?.length ?? 0} failed companies in this sector
            </p>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Failure Patterns */}
            <div>
              <h3 className="text-sm font-semibold text-slate-700 mb-2">Failure Patterns</h3>
              <ul className="space-y-2">
                {data.postmortem_brief.failure_patterns.map((p, i) => (
                  <li key={i} className="flex gap-2 text-sm text-slate-700">
                    <span className="text-red-500 font-bold shrink-0">!</span>
                    {p}
                  </li>
                ))}
              </ul>
            </div>

            {/* Structural Vulnerabilities */}
            {data.postmortem_brief.structural_vulnerabilities?.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-slate-700 mb-2">Structural Vulnerabilities</h3>
                <ul className="space-y-2">
                  {data.postmortem_brief.structural_vulnerabilities.map((v, i) => (
                    <li key={i} className="flex gap-2 text-sm text-slate-600">
                      <span className="text-amber-500 shrink-0">&#x26A0;</span>
                      {v}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Cautionary Narratives */}
            {data.postmortem_brief.cautionary_narratives?.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-slate-700 mb-2">Cautionary Narratives</h3>
                <div className="space-y-3">
                  {data.postmortem_brief.cautionary_narratives.map((n: CautionaryNarrative, i: number) => (
                    <div key={i} className="border rounded-lg p-4 bg-slate-50">
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <h4 className="font-semibold text-slate-900 text-sm">{n.company}</h4>
                        {n.failure_mode && (
                          <Badge variant="outline" className="text-xs border-slate-300 text-slate-600">{n.failure_mode}</Badge>
                        )}
                      </div>
                      {n.peak_position && (
                        <p className="text-sm text-slate-600 mb-1"><span className="font-medium">At their peak:</span> {n.peak_position}</p>
                      )}
                      {n.narrative && (
                        <p className="text-sm text-slate-600 mb-2">{n.narrative}</p>
                      )}
                      {n.key_lesson && (
                        <p className="text-sm text-slate-800 bg-slate-100 rounded p-2 border border-slate-200">
                          <span className="font-medium">Key lesson:</span> {n.key_lesson}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Survival Principles */}
            {data.postmortem_brief.survival_principles?.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-slate-700 mb-2">Survival Principles</h3>
                <ol className="space-y-2 list-decimal list-inside">
                  {data.postmortem_brief.survival_principles.map((p, i) => (
                    <li key={i} className="text-sm text-slate-700">
                      {p}
                    </li>
                  ))}
                </ol>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Parameter cards by category */}
      <div>
        <h2 className="text-xl font-semibold mb-4">Parameter Analysis</h2>
        <div className="space-y-6">
          {Object.entries(categories).map(([category, paramIds]) => (
            <div key={category}>
              <h3 className="text-lg font-medium text-gray-700 mb-3">{category}</h3>
              <div className="grid gap-4 md:grid-cols-2">
                {paramIds.map((paramId) => {
                  const a = analyses[paramId];
                  if (!a) return null;
                  const name =
                    parameter_definitions[paramId]?.name || paramId;
                  const confClass = getConfidenceColor(a.confidence);
                  return (
                    <Card
                      key={paramId}
                      className="cursor-pointer hover:shadow-md transition-shadow"
                      onClick={() => setOpenParamId(paramId)}
                    >
                      <CardContent className="pt-4">
                        <div className="flex items-start justify-between gap-2 mb-2">
                          <h4 className="font-semibold text-gray-900">{name}</h4>
                          <Badge variant="secondary" className={confClass}>
                            {a.confidence}
                          </Badge>
                        </div>
                        <p className="text-sm text-gray-700 mb-3 line-clamp-2">
                          {a.headline || "No headline."}
                        </p>
                        <ol className="list-decimal list-inside text-sm text-gray-600 mb-3">
                          {(a.rankings || []).slice(0, 5).map((r, i) => (
                            <li key={i}>
                              {r.company}
                              {r.label ? ` — ${r.label}` : ""}
                            </li>
                          ))}
                        </ol>
                        <button
                          type="button"
                          className="text-primary text-sm font-medium hover:underline"
                          onClick={(e) => {
                            e.stopPropagation();
                            setOpenParamId(paramId);
                          }}
                        >
                          Read Full Analysis
                        </button>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Modal for full analysis */}
      <Dialog open={!!openParamId} onOpenChange={() => setOpenParamId(null)}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          {activeAnalysis && (
            <>
              <DialogHeader>
                <DialogTitle>{activeAnalysis.parameter_name}</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <h4 className="text-sm font-medium text-gray-600 mb-1">
                    Executive Summary
                  </h4>
                  <p className="text-sm text-gray-700">
                    {activeAnalysis.executive_summary || "—"}
                  </p>
                </div>
                {activeAnalysis.positioning_table &&
                  activeAnalysis.positioning_table.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-600 mb-2">
                        Positioning
                      </h4>
                      <div className="overflow-x-auto border rounded-md">
                        <table className="min-w-full text-sm">
                          <thead>
                            <tr className="bg-gray-50 border-b">
                              {Object.keys(activeAnalysis.positioning_table[0]).map(
                                (k) => (
                                  <th
                                    key={k}
                                    className="px-3 py-2 text-left font-medium"
                                  >
                                    {k}
                                  </th>
                                )
                              )}
                            </tr>
                          </thead>
                          <tbody>
                            {activeAnalysis.positioning_table.map((row, i) => (
                              <tr key={i} className="border-b last:border-0">
                                {Object.values(row).map((v, j) => (
                                  <td key={j} className="px-3 py-2">
                                    {String(v ?? "")}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                <div>
                  <h4 className="text-sm font-medium text-gray-600 mb-2">
                    Full Analysis
                  </h4>
                  <div className="prose prose-sm max-w-none text-gray-700 whitespace-pre-wrap">
                    {activeAnalysis.full_report_markdown || "—"}
                  </div>
                </div>
                {(activeAnalysis.white_space?.length > 0 ||
                  activeAnalysis.trends?.length > 0) && (
                  <div className="grid gap-4 md:grid-cols-2">
                    {activeAnalysis.white_space?.length > 0 && (
                      <div>
                        <h4 className="text-sm font-medium text-gray-600 mb-2">
                          White Space
                        </h4>
                        <ul className="list-disc pl-5 text-sm">
                          {activeAnalysis.white_space.map((w, i) => (
                            <li key={i}>{w}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {activeAnalysis.trends?.length > 0 && (
                      <div>
                        <h4 className="text-sm font-medium text-gray-600 mb-2">
                          Trends
                        </h4>
                        <ul className="list-disc pl-5 text-sm">
                          {activeAnalysis.trends.map((t, i) => (
                            <li key={i}>{t}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
                {activeAnalysis.sources && activeAnalysis.sources.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-600 mb-2">
                      Sources
                    </h4>
                    <ul className="space-y-2">
                      {activeAnalysis.sources.map((s, i) => (
                        <li key={i}>
                          <a
                            href={s.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary text-sm hover:underline"
                          >
                            {s.title || s.url}
                          </a>
                          {s.domain && (
                            <span className="text-xs text-gray-500 ml-2">
                              {s.domain}
                            </span>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
