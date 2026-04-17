// Copyright (c) 2021-2025 Drew Edwards
// This file is part of KanjiSchool under AGPL-3.0.
// Full details: https://github.com/Lemmmy/KanjiSchool/blob/master/LICENSE

import { useState } from "react";
import { Form, Input, Button, Row, Col, Divider, Tabs } from "antd";
import useBreakpoint from "antd/es/grid/hooks/useBreakpoint";

import { AppLoading } from "@global/AppLoading";
import { PageLayout } from "@layout/PageLayout";

import * as api from "@api";
import { loginStandaloneAccount, registerStandaloneAccount } from "@api";

import { SimpleCard } from "@comp/SimpleCard.tsx";
import { ExtLink } from "@comp/ExtLink";
import { DemoCarousel } from "./DemoCarousel";
import { AttributionFooter } from "@layout/AttributionFooter.tsx";

const UUID_RE = /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/;

interface FormValues {
  apiKey: string;
}

export function LoginPage(): JSX.Element {
  const [loggingIn, setLoggingIn] = useState(false);
  const [loginFailed, setLoginFailed] = useState(false);

  const [form] = Form.useForm<FormValues>();

  const { md } = useBreakpoint();

  async function onSubmit() {
    const values = await form.validateFields();

    try {
      // Attempt to log in. If it's successful, save the API key.
      setLoggingIn(true);
      setLoginFailed(false);

      await api.attemptLogIn(values.apiKey);
    } catch (err: any) {
      console.error("login failed:", err);
      setLoginFailed(true);
    } finally {
      setLoggingIn(false);
    }
  }

  async function onRegisterStandalone() {
    try {
      setLoggingIn(true);
      await api.registerStandaloneAccount();
    } catch (err) {
      console.error("standalone registration failed:", err);
    } finally {
      setLoggingIn(false);
    }
  }

  // Logging in screen preloader
  if (loggingIn) {
    return <AppLoading title="Logging in..." />;
  }

  // Actually show the login page
  return <PageLayout
    siteTitle="Log in"
    noHeader
    verticallyCentered
    contentsHeightClassName="h-auto min-h-screen"
  >
    <SimpleCard title="KanjiSchool" className="min-w-[300px] w-full max-w-[720px] box-border relative">
      {/* Top section - lead text and carousel */}
      <Row>
        {/* Lead text */}
        <Col flex="1">
          <p className="mt-0 text-justify">
            Welcome to KanjiSchool, a client for <ExtLink href="https://www.wanikani.com">WaniKani</ExtLink>, an SRS
            kanji learning app created by <ExtLink href="https://www.tofugu.com">Tofugu</ExtLink>.
          </p>

          <p className="mb-0 text-justify">
            The client is fully-featured and supports additional
            functionality such as self-study reviews, mobile support, and
            offline mode.
          </p>
        </Col>

        {/* Carousel on widescreen */}
        {md && <Col flex="200px">
          <DemoCarousel />
        </Col>}
      </Row>

      <Divider />

      <Tabs
        defaultActiveKey="wanikani"
        items={[
          {
            key: "wanikani",
            label: "WaniKani API",
            children: (
              <>
                <p className="text-justify">
                  To get started with your existing WaniKani data, enter your <ExtLink href="https://www.wanikani.com/settings/personal_access_tokens">WaniKani
                  API v2 key</ExtLink>.
                </p>

                <Form
                  form={form}
                  layout="vertical"
                  initialValues={{ apiKey: "" }}
                  onFinish={onSubmit}
                  className="w-full"
                >
                  <Form.Item
                    name="apiKey"
                    label="API Key"
                    required
                    rules={[{
                      pattern: UUID_RE,
                      message: "Must be a valid API key"
                    }]}
                    validateStatus={loginFailed ? "error" : undefined}
                    help={loginFailed ? "Login failed, incorrect API key?" : undefined}
                  >
                    <Input
                      type="password"
                      placeholder="API Key"
                      autoComplete="current-password"
                    />
                  </Form.Item>

                  <Button
                    type="primary"
                    onClick={onSubmit}
                    size="large"
                    block
                  >
                    Log in with WaniKani
                  </Button>
                </Form>
              </>
            )
          },
          {
            key: "login",
            label: "Standalone Login",
            children: (
              <>
                <p className="text-justify mb-sm">
                  Log in to your <strong>standalone</strong> Hanachan account.
                </p>
                <Form
                  layout="vertical"
                  onFinish={(v) => loginStandaloneAccount(v.email, v.password).catch(() => setLoginFailed(true))}
                >
                  <Form.Item name="email" label="Email" required rules={[{ type: 'email' }]}>
                    <Input placeholder="Email" />
                  </Form.Item>
                  <Form.Item name="password" label="Password" required>
                    <Input.Password placeholder="Password" />
                  </Form.Item>
                  <Button type="primary" htmlType="submit" size="large" block>
                    Log In
                  </Button>
                </Form>
              </>
            )
          },
          {
            key: "signup",
            label: "Create Account",
            children: (
              <>
                <p className="text-justify mb-sm">
                  Create a fully independent account. No WaniKani required.
                </p>
                <Form
                  layout="vertical"
                  onFinish={(v) => registerStandaloneAccount(v.email, v.password, v.username).catch(() => setLoginFailed(true))}
                >
                  <Form.Item name="username" label="Username">
                    <Input placeholder="Username (optional)" />
                  </Form.Item>
                  <Form.Item name="email" label="Email" required rules={[{ type: 'email', message: 'Enter a valid email' }]}>
                    <Input placeholder="Email" />
                  </Form.Item>
                  <Form.Item name="password" label="Password" required rules={[{ min: 6, message: 'Password must be at least 6 characters' }]}>
                    <Input.Password placeholder="Password" />
                  </Form.Item>
                  <Button type="primary" htmlType="submit" size="large" block className="bg-green-600 hover:bg-green-700 border-none">
                    Create Standalone Account
                  </Button>
                </Form>
              </>
            )
          }
        ]}
      />

      {/* Carousel on mobile */}
      {!md && <>
        <Divider />
        <Row className="mt-lg justify-center">
          <Col><DemoCarousel /></Col>
        </Row>
      </>}
    </SimpleCard>

    {/* Footer */}
    <AttributionFooter
      withThemeToggle
      className="max-w-[720px] mt-5 mx-auto"
    />
  </PageLayout>;
}
