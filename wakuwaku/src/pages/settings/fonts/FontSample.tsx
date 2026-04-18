// Copyright (c) 2023-2025 Drew Edwards
// This file is part of WakuWaku under AGPL-3.0.
// Full details: https://github.com/Lemmmy/WakuWaku/blob/master/LICENSE

interface FontSampleProps {
  font: string;
  sampleText: string;
}

export function FontSample({ font, sampleText }: FontSampleProps): JSX.Element {
  return <div className="text-[24px] leading-none" style={{ fontFamily: font }}>
    {sampleText}
  </div>;
}
