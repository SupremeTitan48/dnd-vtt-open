import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CharacterSheetPanel } from "./CharacterSheetPanel";
import { ExtensionsManagerPanel } from "./ExtensionsManagerPanel";
import { MacroPanel } from "./MacroPanel";
import { PluginPanel } from "./PluginPanel";
import { RollTemplatePanel } from "./RollTemplatePanel";

describe("Phase 4 panels", () => {
  afterEach(() => {
    cleanup();
  });

  it("hides macro panel for non-GM users", () => {
    render(<MacroPanel macros={[]} canManage={false} onCreate={vi.fn()} onRun={vi.fn()} />);
    expect(screen.queryByText("Macros")).toBeNull();
  });

  it("parses macro variables from newline-separated key=value input", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn().mockResolvedValue("ok");
    render(
      <MacroPanel
        macros={[
          {
            macro_id: "m1",
            name: "Cast",
            template: "{actor} casts {spell}",
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
        ]}
        canManage
        onCreate={vi.fn()}
        onRun={onRun}
      />,
    );

    await user.selectOptions(screen.getByRole("combobox"), "m1");
    await user.clear(screen.getByPlaceholderText("Variables (key=value per line or comma separated)"));
    await user.type(screen.getByPlaceholderText("Variables (key=value per line or comma separated)"), "actor=Nyx{enter}spell=Shield");
    await user.click(screen.getByRole("button", { name: "Run Macro" }));

    expect(onRun).toHaveBeenCalledWith("m1", { actor: "Nyx", spell: "Shield" });
  });

  it("hides roll template panel for non-GM users", () => {
    render(<RollTemplatePanel rollTemplates={[]} canManage={false} onCreate={vi.fn()} onRender={vi.fn()} />);
    expect(screen.queryByText("Roll Templates")).toBeNull();
  });

  it("parses action blocks and runtime variables from newline-separated input", async () => {
    const user = userEvent.setup();
    const onCreate = vi.fn().mockResolvedValue(undefined);
    const onRender = vi.fn().mockResolvedValue("rendered");
    render(
      <RollTemplatePanel
        rollTemplates={[
          {
            roll_template_id: "rt1",
            name: "Attack",
            template: "{actor} uses {attack}",
            action_blocks: { attack: "Longsword" },
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
        ]}
        canManage
        onCreate={onCreate}
        onRender={onRender}
      />,
    );

    await user.type(screen.getByPlaceholderText("Template name"), "New Template");
    fireEvent.change(screen.getByPlaceholderText("Template: {actor} uses {attack} to roll {roll}."), {
      target: { value: "{actor} uses {attack} to roll {roll}." },
    });
    await user.clear(screen.getByPlaceholderText("Action blocks (key=value per line or comma separated)"));
    await user.type(screen.getByPlaceholderText("Action blocks (key=value per line or comma separated)"), "attack=Longsword{enter}roll=1d20+5");
    await user.click(screen.getByRole("button", { name: "Create Roll Template" }));

    expect(onCreate).toHaveBeenCalledWith("New Template", "{actor} uses {attack} to roll {roll}.", {
      attack: "Longsword",
      roll: "1d20+5",
    });

    await user.selectOptions(screen.getByRole("combobox"), "rt1");
    await user.clear(screen.getByPlaceholderText("Runtime variables (key=value per line or comma separated)"));
    await user.type(screen.getByPlaceholderText("Runtime variables (key=value per line or comma separated)"), "actor=Nyx");
    await user.click(screen.getByRole("button", { name: "Render" }));

    expect(onRender).toHaveBeenCalledWith("rt1", { actor: "Nyx" });
  });

  it("hides plugin panel for non-GM users", () => {
    render(<PluginPanel plugins={[]} canManage={false} onRegister={vi.fn()} onExecuteHook={vi.fn()} />);
    expect(screen.queryByText("Plugins")).toBeNull();
  });

  it("validates install flow and toggles modules", async () => {
    const user = userEvent.setup();
    const onInstall = vi.fn().mockResolvedValue(undefined);
    const onToggle = vi.fn().mockResolvedValue(undefined);
    render(
      <ExtensionsManagerPanel
        modules={[
          {
            module_id: "starter-pack",
            name: "Starter Pack",
            version: "1.0.0",
            checksum_sha256: "a".repeat(64),
            enabled: true,
            installed_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
        ]}
        canManage
        onInstall={onInstall}
        onToggle={onToggle}
      />,
    );

    fireEvent.change(screen.getByPlaceholderText("Paste pack manifest JSON"), { target: { value: '{"pack_id":"starter-pack"}' } });
    await user.click(screen.getByRole("button", { name: "Install Pack" }));
    expect(onInstall).toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Disable" }));
    expect(onToggle).toHaveBeenCalledWith("starter-pack", false);
  });

  it("resets extension install error as manifest input changes", async () => {
    const user = userEvent.setup();
    const onInstall = vi.fn().mockRejectedValue(new Error("Manifest must be valid JSON"));
    render(
      <ExtensionsManagerPanel
        modules={[]}
        canManage
        onInstall={onInstall}
        onToggle={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Install Pack" }));
    expect(screen.getByText("Manifest JSON is required.")).toBeTruthy();
    fireEvent.change(screen.getByPlaceholderText("Paste pack manifest JSON"), { target: { value: '{"pack_id":"starter-pack"}' } });
    expect(screen.queryByText("Manifest JSON is required.")).toBeNull();
  });

  it("shows validation for malformed macro variables and blocks run", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn().mockResolvedValue("ok");
    render(
      <MacroPanel
        macros={[
          {
            macro_id: "m1",
            name: "Cast",
            template: "{actor} casts {spell}",
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
        ]}
        canManage
        onCreate={vi.fn()}
        onRun={onRun}
      />,
    );
    await user.selectOptions(screen.getByRole("combobox"), "m1");
    await user.clear(screen.getByPlaceholderText("Variables (key=value per line or comma separated)"));
    await user.type(screen.getByPlaceholderText("Variables (key=value per line or comma separated)"), "actor=Nyx{enter}broken");
    await user.click(screen.getByRole("button", { name: "Run Macro" }));
    expect(screen.getByText("Invalid entries: broken")).toBeTruthy();
    expect(onRun).not.toHaveBeenCalled();
  });

  it("shows backend failure feedback when macro run fails", async () => {
    const user = userEvent.setup();
    const onRun = vi.fn().mockRejectedValue(new Error("Permission denied for macro:mutate"));
    render(
      <MacroPanel
        macros={[
          {
            macro_id: "m1",
            name: "Cast",
            template: "{actor} casts {spell}",
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
        ]}
        canManage
        onCreate={vi.fn()}
        onRun={onRun}
      />,
    );
    await user.selectOptions(screen.getByRole("combobox"), "m1");
    await user.click(screen.getByRole("button", { name: "Run Macro" }));
    expect(screen.getByText("Permission denied for macro:mutate")).toBeTruthy();
  });

  it("shows validation for malformed plugin capabilities and blocks register", async () => {
    const user = userEvent.setup();
    const onRegister = vi.fn().mockResolvedValue(undefined);
    render(<PluginPanel plugins={[]} canManage onRegister={onRegister} onExecuteHook={vi.fn()} />);
    await user.type(screen.getByPlaceholderText("Plugin name"), "MyPlugin");
    await user.clear(screen.getByPlaceholderText("Capabilities (one per line or comma separated)"));
    await user.type(screen.getByPlaceholderText("Capabilities (one per line or comma separated)"), "macro:run{enter}badcap");
    await user.click(screen.getByRole("button", { name: "Register Plugin" }));
    expect(screen.getByText("Invalid capabilities (expected domain:action): badcap")).toBeTruthy();
    expect(onRegister).not.toHaveBeenCalled();
  });

  it("shows validation for empty plugin capability segment and blocks register", async () => {
    const user = userEvent.setup();
    const onRegister = vi.fn().mockResolvedValue(undefined);
    render(<PluginPanel plugins={[]} canManage onRegister={onRegister} onExecuteHook={vi.fn()} />);
    await user.type(screen.getByPlaceholderText("Plugin name"), "MyPlugin");
    await user.clear(screen.getByPlaceholderText("Capabilities (one per line or comma separated)"));
    await user.type(screen.getByPlaceholderText("Capabilities (one per line or comma separated)"), "macro:");
    await user.click(screen.getByRole("button", { name: "Register Plugin" }));
    expect(screen.getByText("Invalid capabilities (expected domain:action): macro:")).toBeTruthy();
    expect(onRegister).not.toHaveBeenCalled();
  });

  it("shows backend failure feedback when roll template render fails", async () => {
    const user = userEvent.setup();
    const onRender = vi.fn().mockRejectedValue(new Error("Roll template not found"));
    render(
      <RollTemplatePanel
        rollTemplates={[
          {
            roll_template_id: "rt1",
            name: "Attack",
            template: "{actor} uses {attack}",
            action_blocks: { attack: "Longsword" },
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
        ]}
        canManage
        onCreate={vi.fn()}
        onRender={onRender}
      />,
    );
    await user.selectOptions(screen.getByRole("combobox"), "rt1");
    await user.click(screen.getByRole("button", { name: "Render" }));
    expect(screen.getByText("Roll template not found")).toBeTruthy();
  });

  it("shows backend failure feedback when plugin register fails", async () => {
    const user = userEvent.setup();
    const onRegister = vi.fn().mockRejectedValue(new Error("Permission denied for plugin:mutate"));
    render(<PluginPanel plugins={[]} canManage onRegister={onRegister} onExecuteHook={vi.fn()} />);
    await user.type(screen.getByPlaceholderText("Plugin name"), "Hooks");
    await user.click(screen.getByRole("button", { name: "Register Plugin" }));
    expect(screen.getByText("Permission denied for plugin:mutate")).toBeTruthy();
  });

  it("rolls sheet actions with advantage and visibility toggles", async () => {
    const user = userEvent.setup();
    const onRoll = vi.fn().mockResolvedValue(undefined);
    render(
      <CharacterSheetPanel
        canRoll
        onRoll={onRoll}
        characters={[
          {
            actor_id: "hero-main-token",
            name: "Hero",
            character_class: "Fighter",
            level: 3,
            hit_points: 20,
            current_hit_points: 15,
            max_hit_points: 20,
            armor_class: 16,
            items: [],
          },
        ]}
      />,
    );
    await user.selectOptions(screen.getByLabelText("Advantage"), "advantage");
    await user.selectOptions(screen.getByLabelText("Visibility"), "private");
    await user.click(screen.getByRole("button", { name: "Perception" }));
    expect(onRoll).toHaveBeenCalledWith({
      actor_id: "hero-main-token",
      action_type: "skill",
      action_key: "perception",
      advantage_mode: "advantage",
      visibility_mode: "private",
    });
  });

  it("renders all provided characters and supports sheet update controls", async () => {
    const user = userEvent.setup();
    const onRoll = vi.fn().mockResolvedValue(undefined);
    const onUpdateSheet = vi.fn().mockResolvedValue(undefined);
    render(
      <CharacterSheetPanel
        canRoll
        onRoll={onRoll}
        onUpdateSheet={onUpdateSheet}
        characters={[
          {
            actor_id: "c1",
            name: "Hero One",
            character_class: "Wizard",
            level: 5,
            hit_points: 28,
            current_hit_points: 22,
            max_hit_points: 28,
            armor_class: 14,
            items: ["Rope"],
            concentration: false,
            abilities: { int: 4 },
            saves: { wis: 3 },
            skills: { arcana: { modifier: 5, proficiency: "expertise" } },
            spell_slots: { level_1: { max: 4, current: 3 } },
            inventory: ["Rope"],
          },
          {
            actor_id: "c2",
            name: "Hero Two",
            character_class: "Rogue",
            level: 4,
            hit_points: 24,
            items: [],
          },
          {
            actor_id: "c3",
            name: "Hero Three",
            character_class: "Cleric",
            level: 4,
            hit_points: 26,
            items: [],
          },
          {
            actor_id: "c4",
            name: "Hero Four",
            character_class: "Fighter",
            level: 4,
            hit_points: 34,
            items: [],
          },
        ]}
      />,
    );

    expect(screen.getByText("Hero Four")).toBeTruthy();
    await user.click(screen.getAllByRole("button", { name: "Start Concentration" })[0]);
    expect(onUpdateSheet).toHaveBeenCalledWith("c1", { concentration: true });

    await user.click(screen.getAllByRole("button", { name: "Spend" })[0]);
    expect(onUpdateSheet).toHaveBeenCalledWith("c1", { spell_slots: { level_1: { max: 4, current: 2 } } });

    await user.type(screen.getAllByPlaceholderText("Inventory item")[0], "Potion");
    await user.click(screen.getAllByRole("button", { name: "Add Item" })[0]);
    expect(onUpdateSheet).toHaveBeenCalledWith("c1", { inventory_add: "Potion" });
  });
});
