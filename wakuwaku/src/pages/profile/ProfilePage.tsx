// Copyright (c) 2021-2025 Drew Edwards
// This file is part of WakuWaku under AGPL-3.0.
// Full details: https://github.com/Lemmmy/WakuWaku/blob/master/LICENSE

import { ReactNode } from "react";
import { Button, Space, Tag } from "antd";

import { useUser } from "@api";
import { ExtLink } from "@comp/ExtLink.tsx";
import { SimpleCard } from "@comp/SimpleCard.tsx";
import { PageLayout } from "@layout/PageLayout";
import { SubscriptionStatus } from "@pages/dashboard/SubscriptionStatus.tsx";
import { LogOutButton } from "@pages/settings/LogOutButton.tsx";

import { uppercaseFirst } from "@utils";

import dayjs from "dayjs";
import TimeAgo from "react-timeago";

function ProfilePage(): JSX.Element | null {
  const user = useUser();
  if (!user) return null;

  const sub = user.data.subscription;
  const level = Math.min(user.data.level, sub.max_level_granted);
  const joinedAt = user.data.started_at;
  const periodEndsAt = sub.period_ends_at;

  return <PageLayout
    siteTitle="Profile"
    title="Profile"
    contentsClassName="max-w-[960px] mx-auto md:pt-md"
    headerClassName="max-w-[960px] mx-auto"
  >
    <SubscriptionStatus />

    <SimpleCard className="mb-md">
      <div className="leading-none">
        <LogOutButton />
        <h2 className="inline-block mt-0 mb-md font-medium">{user.data.username}</h2>
      </div>

      <div className="grid gap-md md:grid-cols-2 leading-normal">
        <ProfileField label="Current level" value={`Level ${level}`} />
        <ProfileField label="Access limit" value={`Up to level ${sub.max_level_granted}`} />
        <ProfileField
          label="Subscription"
          value={<div className="flex items-center gap-xs">
            <span>{uppercaseFirst(sub.type)}</span>
            {sub.active && <Tag color="success" className="!mr-0">Active</Tag>}
          </div>}
        />
        <ProfileField
          label="Account ID"
          value={<span className="font-mono text-sm">{user.data.id}</span>}
        />
        <ProfileField
          label="Joined"
          value={joinedAt
            ? <>
              <TimeAgo date={joinedAt} />
              <span className="text-desc"> ({dayjs(joinedAt).format("DD MMM, YYYY")})</span>
            </>
            : "Unknown"}
        />
        <ProfileField
          label={sub.type === "recurring" ? "Renews" : "Subscription period"}
          value={periodEndsAt
            ? <>
              <TimeAgo date={periodEndsAt} />
              <span className="text-desc"> ({dayjs(periodEndsAt).format("DD MMM, YYYY")})</span>
            </>
            : "Not scheduled"}
        />
      </div>
    </SimpleCard>

    <SimpleCard title="Links" className="mb-md">
      <Space wrap>
        <ExtLink href={user.data.profile_url}>
          <Button type="primary">Open WaniKani profile</Button>
        </ExtLink>

        <ExtLink href="https://www.wanikani.com/account">
          <Button>Manage account</Button>
        </ExtLink>

        <ExtLink href="https://www.wanikani.com/account/subscription">
          <Button>Manage subscription</Button>
        </ExtLink>
      </Space>
    </SimpleCard>
  </PageLayout>;
}

function ProfileField({
  label,
  value
}: {
  label: string;
  value: ReactNode;
}): JSX.Element {
  return <div>
    <div className="mb-1 text-desc text-sm">{label}</div>
    <div>{value}</div>
  </div>;
}

export const Component = ProfilePage;
