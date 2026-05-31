/**
 * Configuration for the particle-swarm portfolio landing page.
 * Edit this file to change all content, styling, and behaviour.
 */
export default {
  // The name to render as the point cloud target
  name: 'Michael',

  // Font for rendering the name to sample target points
  font: {
    family: 'Inter',
    weight: '700',
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
    radius: 1.5,
    driftSpeed: 0.3,
  },

  // Optimiser selection and parameters
  optimizer: {
    type: 'pso', // 'pso' | 'adam' | 'sgd'

    sgd: {
      learningRate: 0.15,
      momentum: 0.85,
    },

    adam: {
      learningRate: 5,
      beta1: 0.9,
      beta2: 0.999,
      epsilon: 1e-8,
    },

    pso: {
      inertiaStart: 0.9,
      inertiaEnd: 0.4,
      cognitive: 0.12,
      social: 0.03,
      maxSpeed: 60,
    },
  },

  // Reveal timing
  reveal: {
    durationSeconds: 5,
    stepsPerFrame: 3,
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
    nameScale: 0.35,
    logoGap: 0.08,
    logoHeight: 0.06,
    logoWidth: 0.06,
    logoPadding: 0.04,
  },
};
