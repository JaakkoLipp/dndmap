import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MapEditor } from "./MapEditor";

function getToolButton(label: string) {
  return screen.getByRole("button", { name: label });
}

describe("MapEditor tool selection", () => {
  it("renders the drawing tools including the new Area tool", () => {
    render(<MapEditor />);

    ["Select", "Pan", "Location", "Map Text", "Route", "Trail", "Area"].forEach(
      (label) => {
        expect(getToolButton(label)).toBeInTheDocument();
      }
    );
  });

  it("marks a tool as pressed when selected", () => {
    render(<MapEditor />);

    const areaTool = getToolButton("Area");
    expect(areaTool).toHaveAttribute("aria-pressed", "false");

    fireEvent.click(areaTool);

    expect(areaTool).toHaveAttribute("aria-pressed", "true");
    expect(getToolButton("Select")).toHaveAttribute("aria-pressed", "false");
  });

  it("exposes the fog-of-war reveal tool", () => {
    render(<MapEditor />);

    const revealTool = getToolButton("Reveal");
    fireEvent.click(revealTool);

    expect(revealTool).toHaveAttribute("aria-pressed", "true");
  });
});

describe("MapEditor fog of war", () => {
  it("toggles fog of war from the toolbar", () => {
    render(<MapEditor />);

    const fogToggle = screen.getByRole("button", { name: /Fog of war/ });
    expect(fogToggle).toHaveAttribute("aria-pressed", "false");

    fireEvent.click(fogToggle);

    expect(fogToggle).toHaveAttribute("aria-pressed", "true");
  });
});

describe("MapEditor object editing", () => {
  it("adds a location marker and renames it from the properties panel", () => {
    const { container } = render(<MapEditor />);

    fireEvent.click(getToolButton("Location"));

    const overlay = container.querySelector(".map-overlay");
    expect(overlay).not.toBeNull();

    fireEvent.pointerDown(overlay as Element, {
      button: 0,
      clientX: 120,
      clientY: 90,
      pointerId: 1
    });

    // The new marker is selected and editable in the properties form.
    const nameInput = screen.getByDisplayValue("Settlement 1");
    fireEvent.change(nameInput, { target: { value: "Waterdeep" } });

    // The renamed marker shows up in the Known Locations list.
    const sidebar = screen.getByLabelText("Known locations and map notes");
    expect(within(sidebar).getByText("Waterdeep")).toBeInTheDocument();
  });
});

describe("MapEditor presentation mode", () => {
  it("hides the editing sidebar when entering player view", () => {
    render(<MapEditor />);

    expect(
      screen.getByLabelText("Known locations and map notes")
    ).toBeInTheDocument();

    fireEvent.click(getToolButton("Present"));

    expect(
      screen.queryByLabelText("Known locations and map notes")
    ).not.toBeInTheDocument();
    expect(screen.getByText("Player view")).toBeInTheDocument();
  });
});
