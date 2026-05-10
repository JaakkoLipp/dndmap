"use client";

import dynamic from "next/dynamic";
import Link from "next/link";

const MapEditor = dynamic(
  () => import("../../components/MapEditor").then((mod) => mod.MapEditor),
  { ssr: false }
);

export default function PlaygroundPage() {
  return (
    <>
      <div
        style={{
          position: "fixed",
          top: "1rem",
          left: "1rem",
          zIndex: 50,
          background: "rgba(15, 23, 42, 0.85)",
          color: "#f8fafc",
          padding: "0.5rem 0.875rem",
          borderRadius: "0.5rem",
          fontSize: "0.8125rem"
        }}
      >
        Local playground — changes are not saved.{" "}
        <Link
          href="/campaigns"
          style={{ color: "#60a5fa", textDecoration: "underline" }}
        >
          Open campaigns
        </Link>
      </div>
      <MapEditor />
    </>
  );
}
