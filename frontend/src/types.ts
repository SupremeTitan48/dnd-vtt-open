export type Session = {
  session_id: string;
  session_name: string;
  host_peer_id: string;
  host_peer_token?: string;
  peers: string[];
  created_at: string;
  peer_roles?: Record<string, "GM" | "AssistantGM" | "Player" | "Observer">;
  actor_owners?: Record<string, string[]>;
  characters?: CharacterSheet[];
  notes?: string;
  encounter_templates?: EncounterTemplate[];
};

export type CharacterSheet = {
  name: string;
  character_class: string;
  level: number;
  hit_points: number;
  items: string[];
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
