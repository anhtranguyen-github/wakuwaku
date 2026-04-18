// Copyright (c) 2021-2025 Drew Edwards
// This file is part of WakuWaku under AGPL-3.0.
// Full details: https://github.com/Lemmmy/WakuWaku/blob/master/LICENSE

import { useMemo } from "react";

import { useNavigate } from "react-router-dom";

import { DataPart } from "./analyze";
import { JlptLevels, JoyoGrades } from "@data";
import { gotoSearch, SearchParamsWithoutOrder } from "@api";
import { nts } from "@utils";

import { CardTable, CardTableCell, CardTableCellProps, CardTableRow } from "@pages/dashboard/CardTable.tsx";

interface Props<T extends number> {
  type: "jlpt" | "joyo";
  title: string;
  keys: [T, string][];
  data?: Record<T, DataPart>;
  totals?: DataPart;
}

const searchKeys: SearchParamsWithoutOrder = {
  subjectTypes: ["kanji"],
  sortOrder: "SRS_THEN_TYPE"
};

export function KanjiProgressTable<T extends number>({
  type,
  title,
  keys,
  data,
  totals
}: Props<T>): JSX.Element | null {
  const navigate = useNavigate();

  const headers = useMemo(() =>
    [title, "Total items", "%", "Locked", "In progress", "Passed", "Burned"], [title]);

  if (!data || !totals) return null;

  const formatCount = (value: number): string => nts(value);
  const totalPercentage = totals.total > 0
    ? ((totals.percentage / totals.total) * 100).toFixed(0)
    : "0";

  return <CardTable headers={headers}>
    {/* Individual rows */}
    {keys.map(([k, name]) => {
      const row = data[k];
      if (!row) return null;
      const { percentage, total, locked, inProgress, passed, burned } = row;

      const cellProps: CardTableCellProps = {
        highlight: percentage === 100,
        burned: total === burned
      };

      return <CardTableRow
        key={k}
        onClick={() => gotoSearch(
          navigate,
          type === "jlpt"
            ? { ...searchKeys, jlptLevels: [k as JlptLevels] }
            : { ...searchKeys, joyoGrades: [k as JoyoGrades] },
          true,
          true
        )}
        clickable
        highlight={percentage === 100}
        burned={total === burned}
      >
        <CardTableCell {...cellProps}>{name}</CardTableCell>
        <CardTableCell {...cellProps}>{formatCount(total)}</CardTableCell>
        <CardTableCell {...cellProps}>{percentage.toFixed(0)}%</CardTableCell>
        <CardTableCell {...cellProps}>{formatCount(locked)}</CardTableCell>
        <CardTableCell {...cellProps}>{formatCount(inProgress)}</CardTableCell>
        <CardTableCell {...cellProps}>{formatCount(passed)}</CardTableCell>
        <CardTableCell {...cellProps}>{formatCount(burned)}</CardTableCell>
      </CardTableRow>;
    })}

    {/* Total row */}
    <CardTableRow className="font-bold bg-black/8">
      <CardTableCell>Total</CardTableCell>
      <CardTableCell>{formatCount(totals.total)}</CardTableCell>
      <CardTableCell>{totalPercentage}%</CardTableCell>
      <CardTableCell>{formatCount(totals.locked)}</CardTableCell>
      <CardTableCell>{formatCount(totals.inProgress)}</CardTableCell>
      <CardTableCell>{formatCount(totals.passed)}</CardTableCell>
      <CardTableCell>{formatCount(totals.burned)}</CardTableCell>
    </CardTableRow>
  </CardTable>;
}
