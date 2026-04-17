export type Session = {
  session_id: string;
  session_name: string;
  host_peer_id: string;
  campaign_id?: string;
  host_peer_token?: string;
  peers: string[];
  created_at: string;
  peer_roles?: Record<string, "GM" | "AssistantGM" | "Player" | "Observer">;
  actor_owners?: Record<string, string[]>;
  journal_entries?: JournalEntry[];
  handouts?: Handout[];
  asset_library?: AssetLibraryItem[];
  characters?: CharacterSheet[];
  notes?: string;
  encounter_templates?: EncounterTemplate[];
};

export type SharedContent = {
  shared_roles: string[];
  shared_peer_ids: string[];
  editable_roles: string[];
  editable_peer_ids: string[];
};

export type JournalEntry = SharedContent & {
  entry_id: string;
  title: string;
  content: string;
  created_at: string;
  updated_at: string;
};

export type Handout = SharedContent & {
  handout_id: string;
  title: string;
  body: string;
  created_at: string;
  updated_at: string;
};

export type AssetLibraryItem = {
  asset_id: string;
  name: string;
  asset_type: string;
  uri: string;
  tags: string[];
  license?: string | null;
  created_at?: string;
};

export type MacroExecution = {
  execution_id: string;
  macro_id: string;
  result: string;
  variables: Record<string, string>;
  actor_peer_id?: string;
  executed_at: string;
};

export type Macro = {
  macro_id: string;
  name: string;
  template: string;
  created_at: string;
  updated_at: string;
};

export type RollTemplateRender = {
  render_id: string;
  roll_template_id: string;
  rendered: string;
  variables: Record<string, string>;
  actor_peer_id?: string;
  rendered_at: string;
};

export type RollTemplate = {
  roll_template_id: string;
  name: string;
  template: string;
  action_blocks: Record<string, string>;
  created_at: string;
  updated_at: string;
};

export type Plugin = {
  plugin_id: string;
  name: string;
  version: string;
  capabilities: string[];
  created_at: string;
};

export type ModulePack = {
  module_id: string;
  name: string;
  version: string;
  description?: string;
  checksum_sha256: string;
  enabled: boolean;
  installed_at: string;
  updated_at: string;
};

export type CharacterSheet = {
  actor_id?: string;
  name: string;
  character_class: string;
  level: number;
  hit_points: number;
  items: string[];
  saves?: Record<string, number>;
  abilities?: Record<string, number>;
  skills?: Record<string, { modifier: number; proficiency: "none" | "half_proficient" | "proficient" | "expertise" | "expert" | number }>;
  attacks?: Record<string, { modifier: number }>;
  spells?: Record<string, { modifier: number }>;
  armor_class?: number;
  max_hit_points?: number;
  current_hit_points?: number;
  concentration?: boolean;
  spell_slots?: Record<string, { max: number; current: number }>;
  inventory?: string[];
};

export type EncounterTemplate = {
  template_name: string;
  description: string;
};

export type Snapshot = {
  revision?: number;
  schema_version?: number;
  map: {
    width: number;
    height: number;
    token_positions: Record<string, [number, number]>;
    fog_enabled: boolean;
    revealed_cells: [number, number][];
    terrain_tiles: Record<string, string>;
    blocked_cells: [number, number][];
    asset_stamps: Record<string, string>;
    visibility_cells_by_token?: Record<string, [number, number][]>;
    vision_radius_by_token?: Record<string, number>;
    vision_mode_by_token?: Record<string, "normal" | "darkvision" | "truesight">;
    token_light_by_token?: Record<
      string,
      { bright_radius: number; dim_radius: number; color: string; enabled: boolean }
    >;
    scene_lighting_preset?: "day" | "dim" | "night";
  };
  combat: {
    initiative_order: string[];
    turn_index: number;
    round_number: number;
  };
  actors: Record<string, { hit_points: number; held_items: string[]; conditions: string[] }>;
};

export type Tutorial = {
  tutorial_id: string;
  title: string;
  estimated_minutes: number;
  steps: string[];
};

export type SessionEvent = {
  event_id: string;
  event_type: string;
  session_id: string;
  revision?: number;
  timestamp: string;
  payload: Record<string, unknown>;
};

export type ChatMessage = {
  message_id: string;
  sender_peer_id?: string;
  kind: "ic" | "ooc" | "emote" | "system" | "whisper" | "roll";
  content?: string;
  visibility_mode: "public" | "private" | "gm_only";
  whisper_targets?: string[];
  revision?: number;
};
