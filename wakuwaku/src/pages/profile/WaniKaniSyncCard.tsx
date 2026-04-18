// Copyright (c) 2021-2025 Drew Edwards
// This file is part of WakuWaku under AGPL-3.0.
// Full details: https://github.com/Lemmmy/WakuWaku/blob/master/LICENSE

import { useState } from "react";
import { Alert, Button, Form, Input, Space } from "antd";

import {
  clearCachedUserProgressData,
  preflightWaniKaniSync,
  syncAll,
  syncWaniKaniData,
  WaniKaniSyncMode,
  WaniKaniSyncPreflight
} from "@api";
import { db } from "@db";
import { globalNotification } from "@global/AntInterface.tsx";
import { SimpleCard } from "@comp/SimpleCard.tsx";

const UUID_RE = /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i;

interface FormValues {
  apiKey: string;
}

interface BrowserCounts {
  assignments: number;
  reviewStatistics: number;
  levelProgressions: number;
  reviews: number;
  queue: number;
}

export function WaniKaniSyncCard(): JSX.Element {
  const [form] = Form.useForm<FormValues>();
  const [checking, setChecking] = useState(false);
  const [syncingMode, setSyncingMode] = useState<WaniKaniSyncMode | null>(null);
  const [error, setError] = useState<string>();
  const [preflight, setPreflight] = useState<(WaniKaniSyncPreflight & {
    browserCounts: BrowserCounts;
    combinedWarnings: string[];
  }) | null>(null);

  async function onCheck() {
    const { apiKey } = await form.validateFields();
    setChecking(true);
    setError(undefined);

    try {
      const [result, browserCounts] = await Promise.all([
        preflightWaniKaniSync(apiKey),
        getBrowserCounts(),
      ]);

      const combinedWarnings = [...result.warnings];
      if (browserCounts.queue > 0) {
        combinedWarnings.push(
          `This browser has ${browserCounts.queue} queued offline submission${browserCounts.queue === 1 ? "" : "s"}. Replace will clear them.`
        );
      }

      setPreflight({
        ...result,
        browserCounts,
        combinedWarnings,
      });
    } catch (err: any) {
      console.error(err);
      setPreflight(null);
      setError(err?.message || "Could not validate the WaniKani API key.");
    } finally {
      setChecking(false);
    }
  }

  async function onImport(mode: WaniKaniSyncMode) {
    const { apiKey } = await form.validateFields();
    setSyncingMode(mode);
    setError(undefined);

    try {
      await syncWaniKaniData(apiKey, mode);

      if (mode === "overwrite") {
        await clearCachedUserProgressData();
      }

      await syncAll(true);

      globalNotification.success({
        message: "WaniKani data synced",
        description: mode === "overwrite"
          ? "Current progress was replaced with your WaniKani data."
          : "Your WaniKani data was merged into the current account."
      });

      setPreflight(null);
      form.resetFields();
    } catch (err: any) {
      console.error(err);
      setError(err?.message || "Sync failed.");
    } finally {
      setSyncingMode(null);
    }
  }

  return <SimpleCard title="Import WaniKani Data" className="mb-md">
    <p className="mt-0">
      Enter a WaniKani API v2 key to inspect the account first, then choose whether to merge that data into this account or replace the current progress.
    </p>

    <Form
      form={form}
      layout="vertical"
      initialValues={{ apiKey: "" }}
      onFinish={onCheck}
    >
      <Form.Item
        name="apiKey"
        label="WaniKani API key"
        rules={[{
          pattern: UUID_RE,
          message: "Must be a valid API key"
        }]}
      >
        <Input.Password
          placeholder="WaniKani API v2 key"
          autoComplete="current-password"
        />
      </Form.Item>

      <Space wrap>
        <Button type="primary" onClick={onCheck} loading={checking}>
          Check key
        </Button>

        {preflight && <Button onClick={() => {
          setPreflight(null);
          setError(undefined);
        }}>
          Reset
        </Button>}
      </Space>
    </Form>

    {error && <Alert
      type="error"
      message={error}
      showIcon
      className="mt-md"
    />}

    {preflight && <>
      <Alert
        type={preflight.combinedWarnings.length > 0 ? "warning" : "success"}
        message={preflight.combinedWarnings.length > 0
          ? "Potential mismatches detected"
          : "No mismatches detected"}
        description={preflight.combinedWarnings.length > 0
          ? <ul className="mb-0 pl-lg">
            {preflight.combinedWarnings.map((warning) => <li key={warning}>{warning}</li>)}
          </ul>
          : "The WaniKani account looks compatible with the current account."}
        showIcon
        className="mt-md"
      />

      <div className="grid gap-md mt-md md:grid-cols-2">
        <SyncSummary
          title="Current account"
          rows={[
            ["Username", preflight.local_user.username],
            ["Level", `Level ${preflight.local_user.level}`],
            ["Assignments", String(preflight.server_data_counts.assignments)],
            ["Review stats", String(preflight.server_data_counts.review_statistics)],
            ["Level progressions", String(preflight.server_data_counts.level_progressions)],
            ["Reviews", String(preflight.server_data_counts.reviews)],
          ]}
        />

        <SyncSummary
          title="WaniKani account"
          rows={[
            ["Username", preflight.remote_user.username],
            ["Level", `Level ${preflight.remote_user.level}`],
            ["Recommended action", preflight.recommended_mode === "merge" ? "Merge data" : "Replace current data"],
          ]}
        />
      </div>

      <Space wrap className="mt-md">
        <Button
          type={preflight.recommended_mode === "merge" ? "primary" : "default"}
          onClick={() => onImport("merge")}
          loading={syncingMode === "merge"}
          disabled={!!syncingMode}
        >
          Merge data
        </Button>

        <Button
          danger
          type={preflight.recommended_mode === "overwrite" ? "primary" : "default"}
          onClick={() => onImport("overwrite")}
          loading={syncingMode === "overwrite"}
          disabled={!!syncingMode}
        >
          Replace current data
        </Button>
      </Space>
    </>}
  </SimpleCard>;
}

function SyncSummary({
  title,
  rows
}: {
  title: string;
  rows: [string, string][];
}): JSX.Element {
  return <div className="rounded-lg border border-solid border-[#303030] light:border-[#e0e0e0] p-md">
    <div className="font-semibold mb-sm">{title}</div>
    <div className="grid gap-xs">
      {rows.map(([label, value]) => <div key={label} className="flex justify-between gap-md">
        <span className="text-desc">{label}</span>
        <span className="text-right">{value}</span>
      </div>)}
    </div>
  </div>;
}

async function getBrowserCounts(): Promise<BrowserCounts> {
  return {
    assignments: await db.assignments.count(),
    reviewStatistics: await db.reviewStatistics.count(),
    levelProgressions: await db.levelProgressions.count(),
    reviews: await db.reviews.count(),
    queue: await db.queue.count(),
  };
}
