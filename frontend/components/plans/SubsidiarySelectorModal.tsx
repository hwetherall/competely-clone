"use client";

import type { CompanyProfile } from "@/lib/types";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";

interface SubsidiarySelectorModalProps {
  open: boolean;
  onClose: () => void;
  companies: CompanyProfile[];
  /** When set, show only this company's subsidiaries (single-company mode). */
  companyId?: string | null;
  /** Pre-selected subsidiary names when reopening (e.g. for single-company mode). */
  initialSelected?: string[];
  onConfirm: (selectedSubsidiaries: string[]) => void;
}

export function SubsidiarySelectorModal({
  open,
  onClose,
  companies,
  companyId,
  initialSelected,
  onConfirm,
}: SubsidiarySelectorModalProps) {
  const allWithSubs = companies.filter(
    (c) => c.subsidiaries && c.subsidiaries.length > 0
  );
  const companiesWithSubs =
    companyId != null
      ? allWithSubs.filter((c) => c.id === companyId)
      : allWithSubs;

  /** For each company: main brand first, then subsidiaries (no duplicate). */
  function optionsForCompany(company: CompanyProfile): string[] {
    const mainName = company.brand_name || company.official_name;
    const subs = (company.subsidiaries ?? []).filter((s) => s !== mainName);
    return [mainName, ...subs];
  }

  const [selected, setSelected] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!open) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSelected(
      companyId != null && initialSelected?.length
        ? new Set(initialSelected)
        : new Set()
    );
  }, [open, companyId, initialSelected]);

  const toggle = (name: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const toggleAllForParent = (parentId: string) => {
    const company = companiesWithSubs.find((c) => c.id === parentId);
    if (!company) return;
    const names = optionsForCompany(company);
    const allSelected = names.every((n) => selected.has(n));
    setSelected((prev) => {
      const next = new Set(prev);
      names.forEach((n) => (allSelected ? next.delete(n) : next.add(n)));
      return next;
    });
  };

  const handleConfirm = () => {
    onConfirm(Array.from(selected));
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Select brands or subsidiaries</DialogTitle>
          <DialogDescription>
            Choose which subsidiaries or brands to include in the analysis. Only
            selected items will be used in the rest of the plan.
          </DialogDescription>
        </DialogHeader>
        <div className="max-h-[50vh] overflow-y-auto space-y-4 py-2">
          {companiesWithSubs.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No subsidiaries data available for the validated companies.
            </p>
          ) : (
            companiesWithSubs.map((company) => {
              const options = optionsForCompany(company);
              const mainName = company.brand_name || company.official_name;
              return (
                <div key={company.id} className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Checkbox
                      id={`parent-${company.id}`}
                      checked={options.every((n) => selected.has(n))}
                      onCheckedChange={() => toggleAllForParent(company.id)}
                    />
                    <Label
                      htmlFor={`parent-${company.id}`}
                      className="text-sm font-medium cursor-pointer"
                    >
                      {company.official_name}
                    </Label>
                  </div>
                  <div className="pl-6 flex flex-col gap-2">
                    {options.map((name) => (
                      <div
                        key={name}
                        className={cn(
                          "flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-muted/50",
                          selected.has(name) && "bg-primary/5"
                        )}
                      >
                        <Checkbox
                          id={`sub-${company.id}-${name}`}
                          checked={selected.has(name)}
                          onCheckedChange={() => toggle(name)}
                        />
                        <Label
                          htmlFor={`sub-${company.id}-${name}`}
                          className="text-sm cursor-pointer flex-1"
                        >
                          {name}
                          {name === mainName && (
                            <span className="text-muted-foreground ml-1">
                              (main brand)
                            </span>
                          )}
                        </Label>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={selected.size === 0}
          >
            Use {selected.size} selected
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
