"use client";

import { useState, KeyboardEvent } from "react";
import { X, Plus } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface CompanyInputProps {
  companies: string[];
  onChange: (companies: string[]) => void;
  placeholder?: string;
  className?: string;
}

export function CompanyInput({
  companies,
  onChange,
  placeholder = "Add company...",
  className,
}: CompanyInputProps) {
  const [inputValue, setInputValue] = useState("");

  const addCompany = (company: string) => {
    const trimmed = company.trim();
    if (trimmed && !companies.includes(trimmed)) {
      onChange([...companies, trimmed]);
      setInputValue("");
    }
  };

  const removeCompany = (company: string) => {
    onChange(companies.filter((c) => c !== company));
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addCompany(inputValue);
    } else if (e.key === "Backspace" && !inputValue && companies.length > 0) {
      removeCompany(companies[companies.length - 1]);
    }
  };

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex flex-wrap items-center gap-2 rounded-lg border bg-background p-3 min-h-[52px]">
        {companies.map((company) => (
          <Badge
            key={company}
            variant="secondary"
            className="flex items-center gap-1 px-3 py-1.5 text-sm"
          >
            {company}
            <button
              type="button"
              onClick={() => removeCompany(company)}
              className="ml-1 rounded-full hover:bg-muted-foreground/20 p-0.5"
            >
              <X className="h-3 w-3" />
            </button>
          </Badge>
        ))}
        <div className="flex-1 min-w-[150px]">
          <Input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={companies.length === 0 ? placeholder : "Add another..."}
            className="border-0 shadow-none focus-visible:ring-0 px-1 h-8"
          />
        </div>
      </div>
      
      {inputValue && (
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => addCompany(inputValue)}
          className="w-full"
        >
          <Plus className="h-4 w-4 mr-2" />
          Add "{inputValue}"
        </Button>
      )}

      {/* Suggestions */}
      <div className="flex flex-wrap gap-2">
        <span className="text-xs text-muted-foreground">Suggestions:</span>
        {["Stripe", "Square", "Adyen", "PayPal", "Klarna"].map((suggestion) => (
          !companies.includes(suggestion) && (
            <button
              key={suggestion}
              type="button"
              onClick={() => addCompany(suggestion)}
              className="text-xs text-primary hover:underline"
            >
              + {suggestion}
            </button>
          )
        ))}
      </div>
    </div>
  );
}
