import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { ImageResponse } from "next/og";
import { site } from "@/lib/site";

export const alt = `${site.name} — ${site.tagline}`;
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const dynamic = "force-static";

const INK_GRID = "rgba(255,255,255,0.07)";
const CHALK = "rgba(255,255,255,0.85)";

// A plausible arm: four-seamers up in the zone, splitters diving out the
// bottom, a pair of sliders off the corners. Coordinates are centers within
// the 360x420 illustration box, whose strike zone spans x 80–280, y 60–310.
const pitches = [
  { x: 130, y: 110, color: "#5194C3" },
  { x: 175, y: 95, color: "#5194C3" },
  { x: 225, y: 125, color: "#5194C3" },
  { x: 155, y: 145, color: "#5194C3" },
  { x: 245, y: 105, color: "#5194C3" },
  { x: 160, y: 290, color: "#F18851" },
  { x: 200, y: 300, color: "#F18851" },
  { x: 140, y: 322, color: "#F18851" },
  { x: 182, y: 350, color: "#F18851" },
  { x: 217, y: 332, color: "#F18851" },
  { x: 236, y: 357, color: "#F18851" },
  { x: 122, y: 347, color: "#F18851" },
  { x: 103, y: 240, color: "#C52622" },
  { x: 266, y: 266, color: "#C52622" },
];

export default async function Image() {
  const [sans, mono] = await Promise.all([
    readFile(join(process.cwd(), "src/app/_fonts/Geist-SemiBold.ttf")),
    readFile(join(process.cwd(), "src/app/_fonts/GeistMono-Medium.ttf")),
  ]);

  return new ImageResponse(
    (
      <div
        style={{
          position: "relative",
          display: "flex",
          flexDirection: "column",
          width: "100%",
          height: "100%",
          padding: 64,
          background: "#0F3D2A",
          fontFamily: "Geist",
        }}
      >
        {Array.from({ length: 11 }).map((_, i) => (
          <div
            key={`v${i}`}
            style={{
              position: "absolute",
              left: (i + 1) * 100,
              top: 0,
              width: 1,
              height: 630,
              background: INK_GRID,
            }}
          />
        ))}
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={`h${i}`}
            style={{
              position: "absolute",
              left: 0,
              top: (i + 1) * 105,
              width: 1200,
              height: 1,
              background: INK_GRID,
            }}
          />
        ))}

        <div style={{ display: "flex", alignItems: "center" }}>
          <div
            style={{
              position: "relative",
              display: "flex",
              width: 38,
              height: 46,
              border: "4px solid #7FD3A8",
              borderRadius: 4,
            }}
          >
            <div
              style={{
                position: "absolute",
                right: 3,
                bottom: 3,
                width: 13,
                height: 13,
                borderRadius: 7,
                background: "#7FD3A8",
              }}
            />
          </div>
          <div
            style={{
              marginLeft: 16,
              fontFamily: "GeistMono",
              fontSize: 34,
              color: "#FFFFFF",
            }}
          >
            mound
          </div>
        </div>

        <div
          style={{
            display: "flex",
            flex: 1,
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", flexDirection: "column" }}>
            <div
              style={{
                display: "flex",
                fontSize: 96,
                lineHeight: 1.02,
                letterSpacing: -3.5,
                color: "#7FD3A8",
              }}
            >
              Understand
            </div>
            <div
              style={{
                display: "flex",
                fontSize: 96,
                lineHeight: 1.02,
                letterSpacing: -3.5,
                color: "#FFFFFF",
              }}
            >
              every pitch.
            </div>
            <div
              style={{
                display: "flex",
                marginTop: 30,
                maxWidth: 700,
                fontSize: 26,
                lineHeight: 1.35,
                color: "rgba(255,255,255,0.62)",
              }}
            >
              A CLI and Python toolkit for MLB pitch-level data.
            </div>
          </div>

          <div
            style={{
              position: "relative",
              display: "flex",
              width: 360,
              height: 420,
            }}
          >
            <div
              style={{
                position: "absolute",
                left: 80,
                top: 60,
                width: 200,
                height: 250,
                border: `5px solid ${CHALK}`,
                borderRadius: 2,
              }}
            />
            {[146.7, 213.3].map((x) => (
              <div
                key={`zv${x}`}
                style={{
                  position: "absolute",
                  left: x,
                  top: 60,
                  width: 2,
                  height: 250,
                  background: "rgba(255,255,255,0.22)",
                }}
              />
            ))}
            {[143.3, 226.7].map((y) => (
              <div
                key={`zh${y}`}
                style={{
                  position: "absolute",
                  left: 80,
                  top: y,
                  width: 200,
                  height: 2,
                  background: "rgba(255,255,255,0.22)",
                }}
              />
            ))}
            {pitches.map((pitch) => (
              <div
                key={`${pitch.x}-${pitch.y}`}
                style={{
                  position: "absolute",
                  left: pitch.x - 11,
                  top: pitch.y - 11,
                  width: 22,
                  height: 22,
                  borderRadius: 11,
                  background: pitch.color,
                }}
              />
            ))}
          </div>
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div
            style={{
              display: "flex",
              fontFamily: "GeistMono",
              fontSize: 25,
              color: "#7FD3A8",
            }}
          >
            moundcli.com
          </div>
          <div
            style={{
              display: "flex",
              fontFamily: "GeistMono",
              fontSize: 22,
              color: "rgba(255,255,255,0.45)",
            }}
          >
            pip install mound
          </div>
        </div>
      </div>
    ),
    {
      ...size,
      fonts: [
        { name: "Geist", data: sans, weight: 600, style: "normal" },
        { name: "GeistMono", data: mono, weight: 500, style: "normal" },
      ],
    },
  );
}
