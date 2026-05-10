"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { LogOut, UserMinus, Users } from "lucide-react";
import { useState } from "react";

import { useAuth } from "../providers/AuthProvider";
import {
  api,
  ApiError,
  queryKeys,
  type CampaignMember,
  type CampaignMemberDetail
} from "../../lib/api";
import {
  ROLE_BADGE_COLOR,
  ROLE_LABEL,
  canManageCampaign,
  type Role
} from "../../lib/roles";

type MembersPanelProps = {
  campaignId: string;
  /** Role of the viewer in this campaign, used to gate controls. */
  viewerRole: Role | undefined;
};

const ROLE_OPTIONS: CampaignMember["role"][] = [
  "owner",
  "dm",
  "player",
  "viewer"
];

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function Avatar({ name, src }: { name: string; src: string | null }) {
  if (src) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        alt=""
        height={32}
        src={src}
        style={{
          width: 32,
          height: 32,
          borderRadius: "50%",
          objectFit: "cover"
        }}
        width={32}
      />
    );
  }
  return (
    <span
      aria-hidden
      style={{
        width: 32,
        height: 32,
        borderRadius: "50%",
        background: "rgba(148, 163, 184, 0.25)",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: "0.75rem",
        fontWeight: 600
      }}
    >
      {initials(name)}
    </span>
  );
}

export function MembersPanel({ campaignId, viewerRole }: MembersPanelProps) {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [error, setError] = useState<string | null>(null);

  const membersQuery = useQuery({
    queryKey: queryKeys.campaignMembers(campaignId),
    queryFn: () => api.members.list(campaignId)
  });

  const updateRole = useMutation({
    mutationFn: ({
      userId,
      role
    }: {
      userId: string;
      role: CampaignMember["role"];
    }) => api.members.updateRole(campaignId, userId, role),
    onSuccess: async () => {
      setError(null);
      await queryClient.invalidateQueries({
        queryKey: queryKeys.campaignMembers(campaignId)
      });
      await queryClient.invalidateQueries({
        queryKey: queryKeys.campaignMe(campaignId)
      });
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.detail : "Failed to change role");
    }
  });

  const removeMember = useMutation({
    mutationFn: (userId: string) => api.members.remove(campaignId, userId),
    onSuccess: async () => {
      setError(null);
      await queryClient.invalidateQueries({
        queryKey: queryKeys.campaignMembers(campaignId)
      });
      await queryClient.invalidateQueries({ queryKey: queryKeys.campaigns });
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.detail : "Failed to remove member");
    }
  });

  const canManage = canManageCampaign(viewerRole);
  const members = membersQuery.data ?? [];

  if (membersQuery.isLoading) {
    return <div className="empty-state">Loading members…</div>;
  }

  // In dev/no-auth mode the route returns []. Hide the panel rather than
  // showing an empty section.
  if (members.length === 0 && !user) {
    return null;
  }

  return (
    <div style={{ marginTop: "1.5rem" }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.5rem",
          marginBottom: "0.5rem"
        }}
      >
        <Users size={18} />
        <h2 style={{ fontSize: "1rem", margin: 0 }}>Members</h2>
        <span className="muted-copy" style={{ fontSize: "0.8125rem" }}>
          {members.length}
        </span>
      </div>

      {error ? (
        <div
          className="notice error-notice"
          role="alert"
          style={{ marginBottom: "0.5rem" }}
        >
          {error}
        </div>
      ) : null}

      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {members.map((member) => (
          <MemberRow
            campaignId={campaignId}
            canManage={canManage}
            isSelf={user?.id === member.user_id}
            key={member.user_id}
            member={member}
            onRoleChange={(role) =>
              updateRole.mutate({ userId: member.user_id, role })
            }
            onRemove={() => removeMember.mutate(member.user_id)}
            pending={
              (updateRole.isPending &&
                updateRole.variables?.userId === member.user_id) ||
              (removeMember.isPending &&
                removeMember.variables === member.user_id)
            }
          />
        ))}
      </ul>
    </div>
  );
}

type MemberRowProps = {
  campaignId: string;
  canManage: boolean;
  isSelf: boolean;
  member: CampaignMemberDetail;
  onRoleChange: (role: CampaignMember["role"]) => void;
  onRemove: () => void;
  pending: boolean;
};

function MemberRow({
  canManage,
  isSelf,
  member,
  onRoleChange,
  onRemove,
  pending
}: MemberRowProps) {
  const role = member.role as Role;

  return (
    <li
      style={{
        display: "flex",
        alignItems: "center",
        gap: "0.75rem",
        padding: "0.5rem 0.75rem",
        borderRadius: "0.5rem",
        background: "rgba(15, 23, 42, 0.4)",
        marginBottom: "0.375rem"
      }}
    >
      <Avatar name={member.display_name} src={member.avatar_url} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 600 }}>
          {member.display_name}
          {isSelf ? (
            <span
              className="muted-copy"
              style={{ marginLeft: "0.375rem", fontWeight: 400 }}
            >
              (you)
            </span>
          ) : null}
        </div>
        <div className="muted-copy" style={{ fontSize: "0.75rem" }}>
          Joined {new Date(member.joined_at).toLocaleDateString()}
        </div>
      </div>

      {canManage && !isSelf ? (
        <select
          aria-label={`Role for ${member.display_name}`}
          disabled={pending}
          onChange={(event) =>
            onRoleChange(event.target.value as CampaignMember["role"])
          }
          style={{
            padding: "0.25rem 0.5rem",
            borderRadius: "0.375rem",
            background: "rgba(15, 23, 42, 0.85)",
            color: "#f8fafc",
            border: "1px solid rgba(148, 163, 184, 0.3)",
            fontSize: "0.8125rem"
          }}
          value={member.role}
        >
          {ROLE_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {ROLE_LABEL[option]}
            </option>
          ))}
        </select>
      ) : (
        <span
          aria-label={`Role: ${ROLE_LABEL[role]}`}
          style={{
            padding: "0.125rem 0.5rem",
            borderRadius: "999px",
            background: ROLE_BADGE_COLOR[role],
            color: "white",
            fontSize: "0.6875rem",
            fontWeight: 600,
            letterSpacing: "0.02em",
            textTransform: "uppercase"
          }}
        >
          {ROLE_LABEL[role]}
        </span>
      )}

      {canManage && !isSelf ? (
        <button
          aria-label={`Remove ${member.display_name}`}
          className="subtle-button"
          disabled={pending}
          onClick={() => {
            if (window.confirm(`Remove ${member.display_name} from this campaign?`)) {
              onRemove();
            }
          }}
          style={{ color: "#fb7185", padding: "0.25rem 0.5rem" }}
          type="button"
        >
          <UserMinus size={14} />
        </button>
      ) : null}

      {isSelf && !canManage ? (
        <button
          className="subtle-button"
          disabled={pending}
          onClick={() => {
            if (window.confirm("Leave this campaign?")) {
              onRemove();
            }
          }}
          style={{
            color: "#fb7185",
            display: "inline-flex",
            alignItems: "center",
            gap: "0.25rem",
            padding: "0.25rem 0.5rem"
          }}
          type="button"
        >
          <LogOut size={14} />
          <span>Leave</span>
        </button>
      ) : null}
    </li>
  );
}
