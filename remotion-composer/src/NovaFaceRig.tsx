import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";

import { NOVA_EYELID_PALETTE } from "./NovaEyelidPalette";

const blinkAt = [72, 188, 319, 463, 612, 759, 913, 1068];

function blinkProgress(frame: number, offset = 0) {
  let result = 0;

  for (const t of blinkAt) {
    const value = interpolate(
      frame - offset,
      [t - 3, t - 0.5, t + 0.5, t + 3],
      [0, 1, 1, 0],
      {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      }
    );

    result = Math.max(result, value);
  }

  return result;
}

type EyeLidProps = {
  x: number;
  y: number;
  width: number;
  height: number;
  progress: number;
  palette: {
    top: string;
    mid: string;
    bottom: string;
  };
  id: string;
};

const EyeLid: React.FC<EyeLidProps> = ({
  x,
  y,
  width,
  height,
  progress,
  palette,
  id,
}) => {
  const p = Math.max(0, Math.min(1, progress));

  const topSide = p * height * 0.49;
  const topMiddle = p * height * 0.56;

  const bottomSide = height - p * height * 0.51;
  const bottomMiddle = height - p * height * 0.44;

  const upperLidPath = `
    M 0 0
    H ${width}
    V ${topSide}
    C ${width * 0.75} ${topMiddle},
      ${width * 0.25} ${topMiddle},
      0 ${topSide}
    Z
  `;

  const lowerLidPath = `
    M 0 ${bottomSide}
    C ${width * 0.25} ${bottomMiddle},
      ${width * 0.75} ${bottomMiddle},
      ${width} ${bottomSide}
    L ${width} ${height}
    L 0 ${height}
    Z
  `;

  const eyelidLine = `
    M 0 ${topSide}
    C ${width * 0.25} ${topMiddle},
      ${width * 0.75} ${topMiddle},
      ${width} ${topSide}
  `;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      style={{
        position: "absolute",
        left: x,
        top: y,
        overflow: "visible",
        pointerEvents: "none",
      }}
    >
      <defs>
        <linearGradient
          id={`lid-gradient-${id}`}
          x1="0"
          y1="0"
          x2="0"
          y2="1"
        >
          <stop offset="0%" stopColor={palette.top} />
          <stop offset="52%" stopColor={palette.mid} />
          <stop offset="100%" stopColor={palette.bottom} />
        </linearGradient>
      </defs>

      {/* Upper eyelid */}
      <path
        d={upperLidPath}
        fill={`url(#lid-gradient-${id})`}
      />

      {/* Lower eyelid */}
      <path
        d={lowerLidPath}
        fill={`url(#lid-gradient-${id})`}
      />

      {/* Eyelid contour */}
      <path
        d={eyelidLine}
        fill="none"
        stroke="#654047"
        strokeWidth={1.15}
        strokeLinecap="round"
        opacity={p * 0.78}
      />
    </svg>
  );
};

export const NovaFaceRig: React.FC = () => {
  const frame = useCurrentFrame();

  const rightBlink = blinkProgress(frame);
  const leftBlink = blinkProgress(frame, 0.2);

  const mouthScale =
    0.88 + 0.16 * Math.abs(Math.sin(frame / 4.5));

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#151522",
        overflow: "hidden",
      }}
    >
      <Img
        src={staticFile("nova/nova-face-base.png")}
        style={{
          position: "absolute",
          width: 853,
          height: 1280,
        }}
      />

      {/* Original right eye */}
      <Img
        src={staticFile("nova/nova-right_eye.png")}
        style={{
          position: "absolute",
          left: 297,
          top: 95,
          width: 71,
          height: 66,
        }}
      />

      {/* Original left eye */}
      <Img
        src={staticFile("nova/nova-left_eye.png")}
        style={{
          position: "absolute",
          left: 378,
          top: 125,
          width: 59,
          height: 60,
        }}
      />

      {/* Animated eyelids */}
      <EyeLid
        id="right"
        x={297}
        y={95}
        width={71}
        height={66}
        progress={rightBlink}
        palette={NOVA_EYELID_PALETTE.right}
      />

      <EyeLid
        id="left"
        x={378}
        y={125}
        width={59}
        height={60}
        progress={leftBlink}
        palette={NOVA_EYELID_PALETTE.left}
      />

      {/* Existing mouth animation */}
      <Img
        src={staticFile("nova/nova-mouth.png")}
        style={{
          position: "absolute",
          left: 318,
          top: 176,
          width: 74,
          height: 52,
          transform: `scaleY(${mouthScale})`,
          transformOrigin: "50% 50%",
        }}
      />

      {/* Approved narration - unchanged */}
      {frame < 1200 && (
        <Audio
          src={staticFile("audio/nova.wav")}
          volume={1}
        />
      )}
    </AbsoluteFill>
  );
};
