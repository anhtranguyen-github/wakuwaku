// Copyright (c) 2023-2025 Drew Edwards
// This file is part of WakuWaku under AGPL-3.0.
// Full details: https://github.com/Lemmmy/WakuWaku/blob/master/LICENSE

import { StoredImageMap } from "@api";
import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export interface ImagesSliceState {
  readonly images?: StoredImageMap;
}

const initialState = (): ImagesSliceState => ({
  images: undefined,
});

const imagesSlice = createSlice({
  name: "images",
  initialState,
  reducers: {
    initImages(s, { payload }: PayloadAction<StoredImageMap>) {
      s.images = payload;
    },
  }
});

export const { initImages } = imagesSlice.actions;

export default imagesSlice.reducer;
