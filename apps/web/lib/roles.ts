import type { CampaignMember } from "./api";

export type Role = CampaignMember["role"];

const ROLE_ORDER: Role[] = ["viewer", "player", "dm", "owner"];

export const ROLE_LABEL: Record<Role, string> = {
  owner: "Owner",
  dm: "Dungeon Master",
  player: "Player",
  viewer: "Viewer"
};

export const ROLE_BADGE_COLOR: Record<Role, string> = {
  owner: "#a855f7",
  dm: "#ef4444",
  player: "#10b981",
  viewer: "#64748b"
};

export function roleAtLeast(role: Role | undefined, minimum: Role): boolean {
  if (!role) return false;
  return ROLE_ORDER.indexOf(role) >= ROLE_ORDER.indexOf(minimum);
}

export const canEditMaps = (role: Role | undefined) => roleAtLeast(role, "dm");
export const canCreateInvites = (role: Role | undefined) => roleAtLeast(role, "dm");
export const canAnnotate = (role: Role | undefined) => roleAtLeast(role, "player");
export const canManageCampaign = (role: Role | undefined) => roleAtLeast(role, "owner");
