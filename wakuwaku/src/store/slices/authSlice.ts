// Copyright (c) 2021-2025 Drew Edwards
// This file is part of WakuWaku under AGPL-3.0.
// Full details: https://github.com/Lemmmy/WakuWaku/blob/master/LICENSE

import { ApiUser } from "@api";

import { lsGetObject, lsGetString } from "@utils";
import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export interface AuthSliceState {
  readonly apiKey?: string;
  readonly user?: ApiUser;
}

function isValidStoredUser(user: unknown): user is ApiUser {
  if (!user || typeof user !== "object") return false;

  const maybeUser = user as Partial<ApiUser> & {
    data?: {
      id?: unknown;
      subscription?: {
        max_level_granted?: unknown;
      };
    };
  };

  return typeof maybeUser.data?.id === "string"
    && typeof maybeUser.data?.subscription?.max_level_granted === "number";
}

export const initialState = (): AuthSliceState => ({
  apiKey: lsGetString("apiKey"),
  user: (() => {
    const storedUser = lsGetObject<unknown>("user");
    return isValidStoredUser(storedUser) ? storedUser : undefined;
  })()
});

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    setApiKey(s, action: PayloadAction<string>) {
      s.apiKey = action.payload;
    },
    setUser(s, action: PayloadAction<ApiUser>) {
      s.user = action.payload;
    }
  }
});

export const { setApiKey, setUser } = authSlice.actions;

export default authSlice.reducer;
