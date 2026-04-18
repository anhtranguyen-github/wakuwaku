// Copyright (c) 2021-2025 Drew Edwards
// This file is part of WakuWaku under AGPL-3.0.
// Full details: https://github.com/Lemmmy/WakuWaku/blob/master/LICENSE

import { post } from "./request";

export type WaniKaniSyncMode = "merge" | "overwrite";

export interface WaniKaniSyncPreflight {
  remote_user: {
    username: string;
    level: number;
    profile_url?: string;
    started_at?: string | null;
    subscription?: {
      active?: boolean;
      max_level_granted?: number;
      type?: string;
      period_ends_at?: string | null;
    };
  };
  local_user: {
    id: string;
    username: string;
    level: number;
  };
  server_data_counts: {
    assignments: number;
    review_statistics: number;
    level_progressions: number;
    reviews: number;
  };
  has_existing_progress: boolean;
  recommended_mode: WaniKaniSyncMode;
  warnings: string[];
}

export interface WaniKaniSyncResponse {
  success: boolean;
  mode: WaniKaniSyncMode;
  subjects_synced: number;
  assignments_synced: number;
  review_statistics_synced: number;
}

export const preflightWaniKaniSync = (apiKey: string): Promise<WaniKaniSyncPreflight> =>
  post("/sync/preflight", { api_key: apiKey });

export const syncWaniKaniData = (
  apiKey: string,
  mode: WaniKaniSyncMode
): Promise<WaniKaniSyncResponse> =>
  post("/sync", { api_key: apiKey, mode });
