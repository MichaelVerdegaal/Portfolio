import type { Config } from './config';

export interface Point {
  x: number;
  y: number;
}

export interface LogoPosition {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface TargetResult {
  targets: Point[];
  logoPositions: LogoPosition[];
}

/**
 * Sample target points from text rendered on an offscreen canvas.
 * All coordinates are in reference space (config.canvas.referenceWidth/Height).
 */
export function sampleTextTargets(
  name: string,
  font: Config['font'],
  numPoints: number,
  refWidth: number,
  refHeight: number,
  layout: Config['layout'],
): Point[] {
  const maxDim = 1200;
  const scale = Math.min(1, maxDim / Math.max(refWidth, refHeight));
  const sampleWidth = Math.ceil(refWidth * scale);
  const sampleHeight = Math.ceil(refHeight * scale);

  const offscreen = document.createElement('canvas');
  offscreen.width = sampleWidth;
  offscreen.height = sampleHeight;
  const ctx = offscreen.getContext('2d')!;

  const nameHeight = sampleHeight * layout.nameScale;
  let fontSize = nameHeight * 0.8;
  ctx.font = `${font.weight} ${fontSize}px "${font.family}"`;
  let metrics = ctx.measureText(name);
  const maxWidth = sampleWidth * 0.85;
  if (metrics.width > maxWidth) {
    fontSize *= maxWidth / metrics.width;
  }

  ctx.clearRect(0, 0, sampleWidth, sampleHeight);
  ctx.font = `${font.weight} ${fontSize}px "${font.family}"`;
  ctx.fillStyle = '#ffffff';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';

  const textY = sampleHeight * 0.42;
  ctx.fillText(name, sampleWidth / 2, textY);

  const imageData = ctx.getImageData(0, 0, sampleWidth, sampleHeight);
  const inkPixels = [];

  for (let y = 0; y < sampleHeight; y++) {
    for (let x = 0; x < sampleWidth; x++) {
      const idx = (y * sampleWidth + x) * 4;
      if (imageData.data[idx + 3] > 128) {
        inkPixels.push({ x: x / scale, y: y / scale });
      }
    }
  }

  if (inkPixels.length === 0) {
    const points = [];
    for (let i = 0; i < numPoints; i++) {
      points.push({
        x: refWidth * 0.2 + Math.random() * refWidth * 0.6,
        y: refHeight * 0.3 + Math.random() * refHeight * 0.3,
      });
    }
    return points;
  }

  const points = [];
  if (inkPixels.length >= numPoints) {
    const step = inkPixels.length / numPoints;
    for (let i = 0; i < numPoints; i++) {
      const idx = Math.min(
        inkPixels.length - 1,
        Math.floor(i * step + Math.random() * step)
      );
      points.push({ ...inkPixels[idx] });
    }
  } else {
    for (let i = 0; i < numPoints; i++) {
      const idx = Math.floor(Math.random() * inkPixels.length);
      points.push({
        x: inkPixels[idx].x + (Math.random() - 0.5) * 0.8,
        y: inkPixels[idx].y + (Math.random() - 0.5) * 0.8,
      });
    }
  }

  return points;
}

/**
 * Sample target points from a logo SVG rendered on an offscreen canvas.
 * Returns a promise that resolves to array of {x, y} in canvas coordinates.
 */
export function sampleLogoTargets(
  svgPath: string,
  numPoints: number,
  x: number,
  y: number,
  width: number,
  height: number,
): Promise<Point[]> {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const offscreen = document.createElement('canvas');
      offscreen.width = Math.ceil(width);
      offscreen.height = Math.ceil(height);
      const ctx = offscreen.getContext('2d')!;
      ctx.drawImage(img, 0, 0, width, height);

      const imageData = ctx.getImageData(0, 0, offscreen.width, offscreen.height);
      const inkPixels = [];

      for (let py = 0; py < offscreen.height; py++) {
        for (let px = 0; px < offscreen.width; px++) {
          const idx = (py * offscreen.width + px) * 4;
          if (imageData.data[idx + 3] > 128) {
            inkPixels.push({ x: px + x, y: py + y });
          }
        }
      }

      if (inkPixels.length === 0) {
        const points = [];
        for (let i = 0; i < numPoints; i++) {
          points.push({
            x: x + Math.random() * width,
            y: y + Math.random() * height,
          });
        }
        resolve(points);
        return;
      }

      const points = [];
      for (let i = 0; i < numPoints; i++) {
        const idx = Math.floor(Math.random() * inkPixels.length);
        points.push({ ...inkPixels[idx] });
      }
      resolve(points);
    };

    img.onerror = () => {
      const points = [];
      for (let i = 0; i < numPoints; i++) {
        points.push({
          x: x + Math.random() * width,
          y: y + Math.random() * height,
        });
      }
      resolve(points);
    };

    img.src = svgPath;
  });
}

/**
 * Generate all target positions (name + logos) in reference space.
 * Returns { targets, logoPositions } in reference coordinates.
 */
export async function generateTargets(config: Config, particleCount: number): Promise<TargetResult> {
  const { name, font, logos, layout, canvas: { referenceWidth, referenceHeight } } = config;
  const totalParticles = particleCount || config.particles.count;

  const logoParticlesEach = logos.length > 0 ? Math.floor(totalParticles * 0.08 / logos.length) : 0;
  const logoParticlesTotal = logoParticlesEach * logos.length;
  const nameParticles = totalParticles - logoParticlesTotal;

  const nameTargets = sampleTextTargets(name, font, nameParticles, referenceWidth, referenceHeight, layout);

  const logoHeight = referenceHeight * layout.logoHeight;
  const logoWidth = referenceWidth * layout.logoWidth;
  const logoPadding = referenceWidth * layout.logoPadding;
  const totalLogosWidth = logos.length * logoWidth + (logos.length - 1) * logoPadding;
  const logoStartX = (referenceWidth - totalLogosWidth) / 2;
  const logoY = referenceHeight * (0.42 + layout.nameScale / 2 + layout.logoGap);

  const logoPositions: LogoPosition[] = [];
  const logoTargets: Point[] = [];

  for (let i = 0; i < logos.length; i++) {
    const lx = logoStartX + i * (logoWidth + logoPadding);
    const ly = logoY;
    logoPositions.push({ x: lx, y: ly, width: logoWidth, height: logoHeight });

    const points = await sampleLogoTargets(logos[i].svg, logoParticlesEach, lx, ly, logoWidth, logoHeight);
    logoTargets.push(...points);
  }

  const allTargets = [...nameTargets, ...logoTargets];

  // Sort targets by x-coordinate for better particle-target assignment
  allTargets.sort((a, b) => a.x - b.x || a.y - b.y);

  return { targets: allTargets, logoPositions };
}
