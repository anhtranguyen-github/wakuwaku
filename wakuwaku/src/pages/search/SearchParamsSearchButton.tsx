// Copyright (c) 2023-2025 Drew Edwards
// This file is part of WakuWaku under AGPL-3.0.
// Full details: https://github.com/Lemmmy/WakuWaku/blob/master/LICENSE

import { Button } from "antd";

export interface SearchButtonProps {
  selfStudy?: boolean;
  loading?: boolean;
}

export function SearchParamsSearchButton({
  selfStudy,
  loading
}: SearchButtonProps): JSX.Element {
  return <Button
    type={selfStudy ? undefined : "primary"}
    htmlType="submit"
    loading={loading}
  >
    {selfStudy ? "Preview" : "Search"}
  </Button>;
}
