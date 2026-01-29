"use client";

import { useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";
import { ConfidenceBadge } from "@/components/common/ConfidenceBadge";
import { CellModal } from "./CellModal";
import type { RunDetail, CellData } from "@/lib/types";
import { cn } from "@/lib/utils";

interface ResultsTableProps {
  data: RunDetail;
}

interface SelectedCell {
  company: string;
  variableId: string;
  data: CellData;
}

export function ResultsTable({ data }: ResultsTableProps) {
  const [selectedCell, setSelectedCell] = useState<SelectedCell | null>(null);
  const { companies, variables, grid } = data;

  // Get variable names from the first company's data
  const getVariableName = (variableId: string): string => {
    const firstCompany = companies[0];
    const cellData = grid[firstCompany]?.[variableId];
    return cellData?.variable_name || variableId.replace(/_/g, " ");
  };

  const handleCellClick = (company: string, variableId: string) => {
    const cellData = grid[company]?.[variableId];
    if (cellData) {
      setSelectedCell({ company, variableId, data: cellData });
    }
  };

  const getCellBackground = (confidence: string): string => {
    switch (confidence.toLowerCase()) {
      case "high":
        return "bg-green-50 hover:bg-green-100";
      case "medium":
        return "bg-yellow-50 hover:bg-yellow-100";
      case "low":
        return "bg-red-50 hover:bg-red-100";
      default:
        return "bg-gray-50 hover:bg-gray-100";
    }
  };

  return (
    <>
      <ScrollArea className="w-full rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/50">
              <TableHead className="sticky left-0 z-10 min-w-[200px] bg-muted/50 font-semibold">
                Variable
              </TableHead>
              {companies.map((company) => (
                <TableHead
                  key={company}
                  className="min-w-[280px] text-center font-semibold"
                >
                  {company}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {variables.map((variableId) => (
              <TableRow key={variableId}>
                <TableCell className="sticky left-0 z-10 bg-background font-medium">
                  <div>
                    <div className="font-semibold text-foreground">
                      {getVariableName(variableId)}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {variableId}
                    </div>
                  </div>
                </TableCell>
                {companies.map((company) => {
                  const cellData = grid[company]?.[variableId];
                  if (!cellData) {
                    return (
                      <TableCell
                        key={`${company}-${variableId}`}
                        className="bg-gray-50 text-center text-muted-foreground"
                      >
                        No data
                      </TableCell>
                    );
                  }

                  return (
                    <TableCell
                      key={`${company}-${variableId}`}
                      className={cn(
                        "cursor-pointer transition-colors",
                        getCellBackground(cellData.confidence)
                      )}
                      onClick={() => handleCellClick(company, variableId)}
                    >
                      <div className="space-y-2">
                        <p className="line-clamp-4 text-sm leading-relaxed">
                          {cellData.concise}
                        </p>
                        <div className="flex items-center justify-between">
                          <ConfidenceBadge
                            confidence={cellData.confidence}
                            className="text-xs"
                          />
                          <span className="text-xs text-muted-foreground">
                            {cellData.sources.length} sources
                          </span>
                        </div>
                      </div>
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <ScrollBar orientation="horizontal" />
      </ScrollArea>

      <CellModal
        open={!!selectedCell}
        onOpenChange={(open) => !open && setSelectedCell(null)}
        company={selectedCell?.company || ""}
        variableName={selectedCell?.data.variable_name || ""}
        data={selectedCell?.data || null}
      />
    </>
  );
}
