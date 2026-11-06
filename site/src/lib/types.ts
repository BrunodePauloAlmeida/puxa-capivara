/** Formats produced by the pipeline (`uv run puxa site`, in pipeline/src/puxa/web.py). */

export type Role = "president" | "governor" | "senator" | "federal_deputy";

export interface IndexRow {
  id: string;
  name: string;
  role: string;
  party_state: string;
  state: string | null;
  roles: Role[];
  photo: boolean;
  initials: string;
  search: string;
}

export interface Meta {
  version: string;
  generated_at: string;
  people: number;
  in_office: Record<Role, number>;
  elected_2026: Record<Role, number>;
  with_photo: number;
}

export interface VoteRow {
  title: string;
  yes_means: string;
  house: string;
  date: string;
  vote: string;
  class: "yes" | "no" | "partial" | "neutral" | "empty";
  detail: string;
  outcome: string;
}

export interface Bills {
  house: string;
  since: string;
  first_author: number;
  total: number;
  became_law: number;
  highlights: { identifier: string; law: string | null; summary: string }[];
}

export interface Person {
  id: string;
  name: string;
  civil_name: string;
  initials: string;
  photo_source: string | null;
  roles: string[];
  party_state: string;
  hot_topics: VoteRow[];
  votes: VoteRow[];
  in_congress: boolean;
  bills: Bills | null;
  generated_at: string;
  version: string;
  has_photo: boolean;
  has_pdf: boolean;
}
