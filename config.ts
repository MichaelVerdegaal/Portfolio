export type OptimizerType = 'pso' | 'adam' | 'sgd' | 'rmsprop' | 'muon';

export interface Config {
  name: string;
  font: { family: string; weight: string; url: string };
  palette: {
    background: string;
    points: string;
    pointsAlpha: number;
    button: string;
    buttonText: string;
    buttonHover: string;
    logoAccent: string;
  };
  particles: { count: number; radius: number; driftSpeed: number };
  optimizer: {
    type: OptimizerType;
    muon: { learningRate: number; momentum: number; nsSteps: number };
    sgd: { learningRate: number; momentum: number };
    adam: { learningRate: number; beta1: number; beta2: number; epsilon: number };
    pso: { inertiaStart: number; inertiaEnd: number; cognitive: number; social: number; maxSpeed: number };
    rmsprop: { learningRate: number; alpha: number; epsilon: number; momentum: number };
  };
  reveal: { durationSeconds: number; stepsPerFrame: number };
  logos: Array<{ label: string; svg: string; href: string }>;
  layout: {
    nameScale: number;
    logoGap: number;
    logoHeight: number;
    logoWidth: number;
    logoPadding: number;
  };
  canvas: { referenceWidth: number; referenceHeight: number };
}

const config: Config = {
  name: 'Michael Verdegaal',

  font: {
    family: 'Manrope',
    weight: '700',
    url: 'https://fonts.googleapis.com/css2?family=Manrope:wght@200..800&display=swap',
  },

  palette: {
    background: '#191A1C',
    points: '#ffffff',
    pointsAlpha: 0.85,
    button: '#ffffff',
    buttonText: '#191A1C',
    buttonHover: '#cccccc',
    logoAccent: '#ffffff',
  },

  particles: {
    count: 100000,
    radius: 0.8,
    driftSpeed: 0.3,
  },

  optimizer: {
    type: 'muon',

    muon: {
      learningRate: 30,
      momentum: 0.85,
      nsSteps: 5,
    },

    sgd: {
      learningRate: 0.0005,
      momentum: 0.5,
    },

    adam: {
      learningRate: 0.05,
      beta1: 0.9,
      beta2: 0.999,
      epsilon: 1e-8,
    },

    pso: {
      inertiaStart: 0.4,
      inertiaEnd: 0.2,
      cognitive: 0.5,
      social: 0.5,
      maxSpeed: 0.1,
    },

    rmsprop: {
      learningRate: 0.1,
      alpha: 0.99,
      epsilon: 1e-8,
      momentum: 0,
    },
  },

  reveal: {
    durationSeconds: 30,
    stepsPerFrame: 10,
  },

  logos: [
    {
      label: 'GitHub',
      svg: 'assets/logos/github.svg',
      href: 'https://github.com/MichaelVerdegaal',
    },
    {
      label: 'LinkedIn',
      svg: 'assets/logos/linkedin.svg',
      href: 'https://www.linkedin.com/in/michael-verdegaal-2b8353164/',
    },
    {
      label: 'Email',
      svg: 'assets/logos/email.svg',
      href: 'mailto:mverdegaal@protonmail.com',
    },
  ],

  layout: {
    nameScale: 0.35,
    logoGap: 0.08,
    logoHeight: 0.06,
    logoWidth: 0.06,
    logoPadding: 0.04,
  },

  // Reference resolution: all particle positions and targets are generated
  // in this coordinate space, then uniformly scaled to the actual canvas.
  canvas: {
    referenceWidth: 1920,
    referenceHeight: 1080,
  },
};

export default config;
