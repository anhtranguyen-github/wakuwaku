// Copyright (c) 2021-2025 Drew Edwards
// This file is part of WakuWaku under AGPL-3.0.
// Full details: https://github.com/Lemmmy/WakuWaku/blob/master/LICENSE

import { Comparator } from "../interfaces";

export function reverse<T>(f: Comparator<T>): Comparator<T> {
  return (a, b) => {
    return f(b, a);
  };
}
