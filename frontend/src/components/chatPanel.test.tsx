import { describe, expect, it, vi } from "vitest";
import { afterEach } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { ChatPanel } from "./ChatPanel";
import type { ChatMessage } from "../types";

type ChatPanelSendPayload = Parameters<Parameters<typeof ChatPanel>[0]["onSend"]>[0];
const makeOnSend = () => vi.fn<(payload: ChatPanelSendPayload) => Promise<void>>(async () => {});

afterEach(() => {
  cleanup();
});

describe("ChatPanel", () => {
  it("renders semantic badges for message kinds and visibility", () => {
    const messages: ChatMessage[] = [
      { message_id: "1", kind: "ic", content: "Hello", visibility_mode: "public", whisper_targets: [], sender_peer_id: "p1", revision: 1 },
      { message_id: "2", kind: "ooc", content: "Rules check", visibility_mode: "private", whisper_targets: [], sender_peer_id: "p2", revision: 2 },
      { message_id: "3", kind: "emote", content: "smiles", visibility_mode: "public", whisper_targets: [], sender_peer_id: "p1", revision: 3 },
    ];
    render(<ChatPanel messages={messages} currentPeerId="p1" canPost onSend={makeOnSend()} />);
    expect(screen.getByText("IC")).toBeTruthy();
    expect(screen.getByText("OOC")).toBeTruthy();
    expect(screen.getByText("/me")).toBeTruthy();
    expect(screen.getByText("private")).toBeTruthy();
  });

  it("submits composed message payload", async () => {
    const onSend = makeOnSend();
    render(<ChatPanel messages={[]} currentPeerId="p1" canPost onSend={onSend} />);
    fireEvent.change(screen.getByPlaceholderText("Type message..."), { target: { value: "Hi table" } });
    fireEvent.click(screen.getByText("Send"));
    expect(onSend).toHaveBeenCalledTimes(1);
    expect(onSend.mock.calls[0][0]).toMatchObject({ content: "Hi table", kind: "ic", visibility_mode: "public" });
  });

  it("parses /me and /ooc slash prefixes into message kinds", async () => {
    const onSend = makeOnSend();
    render(<ChatPanel messages={[]} currentPeerId="p1" canPost onSend={onSend} />);
    fireEvent.change(screen.getByPlaceholderText("Type message..."), { target: { value: "/me nods" } });
    fireEvent.click(screen.getByText("Send"));
    fireEvent.change(screen.getByPlaceholderText("Type message..."), { target: { value: "/ooc rules check" } });
    fireEvent.click(screen.getByText("Send"));
    expect(onSend).toHaveBeenCalledTimes(2);
    expect(onSend.mock.calls[0][0]).toMatchObject({ kind: "emote", content: "nods" });
    expect(onSend.mock.calls[1][0]).toMatchObject({ kind: "ooc", content: "rules check" });
  });

  it("sends whisper target payload as trimmed peer list", async () => {
    const onSend = makeOnSend();
    render(<ChatPanel messages={[]} currentPeerId="p1" canPost onSend={onSend} />);
    fireEvent.change(screen.getAllByRole("combobox")[0], { target: { value: "whisper" } });
    fireEvent.change(screen.getByPlaceholderText("Whisper targets (peer ids, comma separated)"), { target: { value: "p2, p3  ,  " } });
    fireEvent.change(screen.getByPlaceholderText("Type message..."), { target: { value: "quietly" } });
    fireEvent.click(screen.getByText("Send"));
    expect(onSend).toHaveBeenCalledTimes(1);
    expect(onSend.mock.calls[0][0]).toMatchObject({ kind: "whisper", whisper_targets: ["p2", "p3"] });
  });

  it("renders whisper target context and hidden fallback content", () => {
    const messages: ChatMessage[] = [
      {
        message_id: "w1",
        kind: "whisper",
        content: "",
        visibility_mode: "public",
        whisper_targets: ["p2", "p3"],
        sender_peer_id: "p1",
        revision: 1,
      },
    ];
    render(<ChatPanel messages={messages} currentPeerId="p1" canPost onSend={makeOnSend()} />);
    expect(screen.getByText("to p2, p3")).toBeTruthy();
    expect(screen.getByText("(hidden)")).toBeTruthy();
  });

  it("renders roll visibility semantics text", () => {
    const messages: ChatMessage[] = [
      {
        message_id: "r1",
        kind: "roll",
        content: "Attack roll",
        visibility_mode: "private",
        whisper_targets: [],
        sender_peer_id: "p1",
        revision: 1,
      },
    ];
    render(<ChatPanel messages={messages} currentPeerId="p1" canPost onSend={makeOnSend()} />);
    expect(screen.getByText("roll: private")).toBeTruthy();
  });

  it("parses /roll and /r into roll kind", async () => {
    const onSend = makeOnSend();
    render(<ChatPanel messages={[]} currentPeerId="p1" canPost onSend={onSend} />);
    fireEvent.change(screen.getByPlaceholderText("Type message..."), { target: { value: "/roll 1d20+5" } });
    fireEvent.click(screen.getByText("Send"));
    fireEvent.change(screen.getByPlaceholderText("Type message..."), { target: { value: "/r stealth check" } });
    fireEvent.click(screen.getByText("Send"));
    expect(onSend).toHaveBeenCalledTimes(2);
    expect(onSend.mock.calls[0]?.[0]).toMatchObject({ kind: "roll", content: "1d20+5" });
    expect(onSend.mock.calls[1]?.[0]).toMatchObject({ kind: "roll", content: "stealth check" });
  });

  it("parses /pr into private roll", async () => {
    const onSend = makeOnSend();
    render(<ChatPanel messages={[]} currentPeerId="p1" canPost onSend={onSend} />);
    fireEvent.change(screen.getByPlaceholderText("Type message..."), { target: { value: "/pr 1d20+7" } });
    fireEvent.click(screen.getByText("Send"));
    expect(onSend).toHaveBeenCalledTimes(1);
    expect(onSend.mock.calls[0]?.[0]).toMatchObject({ kind: "roll", content: "1d20+7", visibility_mode: "private" });
  });
});
