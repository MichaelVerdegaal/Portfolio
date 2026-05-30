/**
 * Target sampling module: renders text and logos to offscreen canvases
 * and samples filled pixels to produce target point coordinates.
 */

/**
 * Sample target points from text rendered on an offscreen canvas.
 * Returns array of {x, y} in canvas coordinates.
 */
export function sampleTextTargets(name, font, numPoints, canvasWidth, canvasHeight, layout) {
  const offscreen = document.createElement('canvas');
  offscreen.width = canvasWidth;
  offscreen.height = canvasHeight;
  const ctx = offscreen.getContext('2d');

  // Calculate font size to fill the designated area
  const nameHeight = canvasHeight * layout.nameScale;
  // Start with a large font and measure, then scale down
  let fontSize = nameHeight * 0.8;
  ctx.font = `${font.weight} ${fontSize}px "${font.family}"`;
  let metrics = ctx.measureText(name);
  // Scale to fit width (leave 10% margin)
  const maxWidth = canvasWidth * 0.85;
  if (metrics.width > maxWidth) {
    fontSize *= maxWidth / metrics.width;
  }

  ctx.clearRect(0, 0, canvasWidth, canvasHeight);
  ctx.font = `${font.weight} ${fontSize}px "${font.family}"`;
  ctx.fillStyle = '#ffffff';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';

  // Position: centered horizontally, in the upper portion
  const textY = canvasHeight * 0.42;
  ctx.fillText(name, canvasWidth / 2, textY);

  // Read pixel data and collect ink positions
  const imageData = ctx.getImageData(0, 0, canvasWidth, canvasHeight);
  const inkPixels = [];

  for (let y = 0; y < canvasHeight; y++) {
    for (let x = 0; x < canvasWidth; x++) {
      const idx = (y * canvasWidth + x) * 4;
      // Alpha channel > threshold means ink
      if (imageData.data[idx + 3] > 128) {
        inkPixels.push({ x, y });
      }
    }
  }

  if (inkPixels.length === 0) {
    // Fallback: random positions
    const points = [];
    for (let i = 0; i < numPoints; i++) {
      points.push({
        x: canvasWidth * 0.2 + Math.random() * canvasWidth * 0.6,
        y: canvasHeight * 0.3 + Math.random() * canvasHeight * 0.3,
      });
    }
    return points;
  }

  // Sample points from ink pixels (with replacement if needed)
  const points = [];
  for (let i = 0; i < numPoints; i++) {
    const idx = Math.floor(Math.random() * inkPixels.length);
    points.push({ ...inkPixels[idx] });
  }

  return points;
}

/**
 * Sample target points from a logo SVG rendered on an offscreen canvas.
 * Returns a promise that resolves to array of {x, y} in canvas coordinates.
 */
export function sampleLogoTargets(svgPath, numPoints, x, y, width, height) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const offscreen = document.createElement('canvas');
      offscreen.width = Math.ceil(width);
      offscreen.height = Math.ceil(height);
      const ctx = offscreen.getContext('2d');
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
        // Fallback: fill the logo area with random points
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
      // Fallback on load error
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
 * Generate all target positions (name + logos) and assign to particles.
 * Returns { targets, logoPositions } where targets is array of {x, y} for each particle
 * and logoPositions is array of {x, y, width, height} for each logo.
 */
export async function generateTargets(config, canvasWidth, canvasHeight) {
  const { name, font, particles, logos, layout } = config;
  const totalParticles = particles.count;

  // Allocate particles between name and logos
  const logoParticlesEach = logos.length > 0 ? Math.floor(totalParticles * 0.08 / logos.length) : 0;
  const logoParticlesTotal = logoParticlesEach * logos.length;
  const nameParticles = totalParticles - logoParticlesTotal;

  // Sample name targets
  const nameTargets = sampleTextTargets(name, font, nameParticles, canvasWidth, canvasHeight, layout);

  // Calculate logo positions
  const logoHeight = canvasHeight * layout.logoHeight;
  const logoWidth = canvasWidth * layout.logoWidth;
  const logoPadding = canvasWidth * layout.logoPadding;
  const totalLogosWidth = logos.length * logoWidth + (logos.length - 1) * logoPadding;
  const logoStartX = (canvasWidth - totalLogosWidth) / 2;
  const logoY = canvasHeight * (0.42 + layout.nameScale / 2 + layout.logoGap);

  const logoPositions = [];
  const logoTargets = [];

  for (let i = 0; i < logos.length; i++) {
    const lx = logoStartX + i * (logoWidth + logoPadding);
    const ly = logoY;
    logoPositions.push({ x: lx, y: ly, width: logoWidth, height: logoHeight });

    const points = await sampleLogoTargets(logos[i].svg, logoParticlesEach, lx, ly, logoWidth, logoHeight);
    logoTargets.push(...points);
  }

  // Combine all targets
  const allTargets = [...nameTargets, ...logoTargets];

  // Sort targets by x-coordinate for better assignment
  allTargets.sort((a, b) => a.x - b.x || a.y - b.y);

  return { targets: allTargets, logoPositions };
}

/**
 * Normalise canvas coordinates to [-1, 1] range for network training.
 */
export function normaliseTargets(targets, canvasWidth, canvasHeight) {
  const normalised = new Float32Array(targets.length * 2);
  for (let i = 0; i < targets.length; i++) {
    // Map [0, width] -> [-1, 1] and [0, height] -> [-1, 1]
    normalised[i * 2] = (targets[i].x / canvasWidth) * 2 - 1;
    normalised[i * 2 + 1] = (targets[i].y / canvasHeight) * 2 - 1;
  }
  return normalised;
}

/**
 * Convert normalised [-1, 1] coordinates back to canvas pixels.
 */
export function denormalise(normX, normY, canvasWidth, canvasHeight) {
  return {
    x: (normX + 1) / 2 * canvasWidth,
    y: (normY + 1) / 2 * canvasHeight,
  };
}
