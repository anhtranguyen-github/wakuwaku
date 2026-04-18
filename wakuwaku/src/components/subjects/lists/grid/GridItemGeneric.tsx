// Copyright (c) 2021-2025 Drew Edwards
// This file is part of WakuWaku under AGPL-3.0.
// Full details: https://github.com/Lemmmy/WakuWaku/blob/master/LICENSE

import { SubjectGridItem, SubjectGridItemProps } from "./SubjectGridItem";

// Generic grid item that does nothing more than display the subject characters.
export function GridItemGeneric({
  subject,
  ...rest
}: SubjectGridItemProps): JSX.Element {
  return <SubjectGridItem
    subject={subject}
    {...rest}
  />;
}
