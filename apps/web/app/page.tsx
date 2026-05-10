"use client";

import dynamic from "next/dynamic";

const MapEditor = dynamic(
  () => import("../components/MapEditor").then((mod) => mod.MapEditor),
  { ssr: false }
);

export default function Home() {
  return <MapEditor />;
}
