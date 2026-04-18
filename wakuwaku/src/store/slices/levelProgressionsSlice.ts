// Copyright (c) 2023-2025 Drew Edwards
// This file is part of WakuWaku under AGPL-3.0.
// Full details: https://github.com/Lemmmy/WakuWaku/blob/master/LICENSE

import { ApiLevelProgressionMap } from "@api";
import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export interface LevelProgressionsSliceState {
  readonly levelProgressions?: ApiLevelProgressionMap;
}

const initialState = (): LevelProgressionsSliceState => ({
  levelProgressions: undefined,
});

const levelProgressionsSlice = createSlice({
  name: "levelProgressions",
  initialState,
  reducers: {
    initLevelProgressions(s, { payload }: PayloadAction<ApiLevelProgressionMap>) {
      s.levelProgressions = payload;
    },
  }
});

export const { initLevelProgressions } = levelProgressionsSlice.actions;

export default levelProgressionsSlice.reducer;
