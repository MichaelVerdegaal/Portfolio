/**
 * Configuration for the neural point-cloud portfolio landing page.
 * Edit this file to change all content, styling, and behaviour.
 */
export default {
  // The name to render as the point cloud target
  name: 'Michael',

  // Font for rendering the name to sample target points
  // Use a web-safe font or load a Google Font in index.html
  font: {
    family: 'Inter',
    weight: '700',
    // Google Fonts URL (loaded in index.html <link>)
    url: 'https://fonts.googleapis.com/css2?family=Inter:wght@700&display=swap',
  },

  // Colour palette
  palette: {
    background: '#000000',
    points: '#ffffff',
    pointsAlpha: 0.85,
    button: '#ffffff',
    buttonText: '#000000',
    buttonHover: '#cccccc',
    logoAccent: '#ffffff',
  },

  // Particle system
  particles: {
    count: 3000,
    // Size of each point in pixels
    radius: 1.5,
    // Idle drift speed multiplier
    driftSpeed: 0.3,
  },

  // Reveal timing
  reveal: {
    // Target duration in seconds for the convergence
    durationSeconds: 5,
    // Mini-batch gradient steps per animation frame
    stepsPerFrame: 5,
    // Learning rate for Adam optimiser
    learningRate: 0.015,
  },

  // Neural network architecture
  network: {
    // Dimension of per-particle input code
    inputDim: 4,
    // Number of random Fourier feature frequencies
    fourierFeatures: 32,
    // Hidden layer sizes
    hiddenLayers: [48, 48],
    // Activation: 'tanh' or 'relu'
    activation: 'tanh',
  },

  // Logos and links displayed beneath the name
  logos: [
    {
      label: 'GitHub',
      svg: 'assets/logos/github.svg',
      href: 'https://github.com/michael',
    },
    {
      label: 'LinkedIn',
      svg: 'assets/logos/linkedin.svg',
      href: 'https://linkedin.com/in/michael',
    },
    {
      label: 'Email',
      svg: 'assets/logos/email.svg',
      href: 'mailto:michael@example.com',
    },
  ],

  // Layout proportions (fraction of canvas)
  layout: {
    // How much vertical space the name occupies (0-1)
    nameScale: 0.35,
    // Gap between name and logos (fraction of canvas height)
    logoGap: 0.08,
    // Logo row height (fraction of canvas height)
    logoHeight: 0.06,
    // Individual logo width (fraction of canvas width)
    logoWidth: 0.06,
    // Gap between logos (fraction of canvas width)
    logoPadding: 0.04,
  },
};
