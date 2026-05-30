/**
 * Neural network module: MLP with Random Fourier Features and Adam optimiser.
 * Hand-written forward pass and backpropagation, no ML libraries.
 *
 * Performance notes:
 *   - Every Float32Array used in the per-frame hot path (training and render
 *     forward passes, gradients, activation caches) is preallocated once and
 *     reused. The previous version allocated a dozen typed arrays per backward
 *     call, which both wasted cycles and produced GC stutter on every frame.
 *   - Buffers are sized lazily to the batch size first seen, then reused. The
 *     render pass (all particles) and the training pass (a mini-batch) keep
 *     separate buffer sets because their batch sizes differ.
 */

const ADAM_BETA1 = 0.9;
const ADAM_BETA2 = 0.999;
const ADAM_EPS = 1e-8;

/**
 * Create a random matrix for Fourier feature encoding.
 * Projects inputDim -> numFrequencies, then sin/cos gives 2*numFrequencies features.
 *
 * @param {number} inputDim Dimension of the raw per-particle input code.
 * @param {number} numFrequencies Number of random frequencies to project onto.
 * @param {number} [scale=8.0] Std of the Gaussian frequencies. Higher = sharper
 *   detail the network can represent (the main knob for crisp glyphs), at the
 *   cost of noisier high-frequency output. 6 to 10 works well for text.
 * @returns {{B: Float32Array, inputDim: number, numFrequencies: number, outputDim: number}}
 */
export function createFourierMatrix(inputDim, numFrequencies, scale = 8.0) {
  const B = new Float32Array(inputDim * numFrequencies);
  for (let i = 0; i < B.length; i++) {
    const u1 = Math.random();
    const u2 = Math.random();
    B[i] = scale * Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
  }
  return { B, inputDim, numFrequencies, outputDim: numFrequencies * 2 };
}

/**
 * Encode a batch of input codes using random Fourier features.
 * Run once at setup, so allocation here is fine.
 *
 * @param {object} fourier Matrix from createFourierMatrix.
 * @param {Float32Array} inputs Row-major [batchSize x inputDim].
 * @param {number} batchSize Number of input codes.
 * @returns {Float32Array} Row-major [batchSize x (numFrequencies * 2)].
 */
export function fourierEncode(fourier, inputs, batchSize) {
  const { B, inputDim, numFrequencies, outputDim } = fourier;
  const encoded = new Float32Array(batchSize * outputDim);

  for (let i = 0; i < batchSize; i++) {
    const inOff = i * inputDim;
    const outOff = i * outputDim;
    for (let j = 0; j < numFrequencies; j++) {
      let dot = 0;
      for (let k = 0; k < inputDim; k++) {
        dot += inputs[inOff + k] * B[k * numFrequencies + j];
      }
      encoded[outOff + j] = Math.sin(dot);
      encoded[outOff + numFrequencies + j] = Math.cos(dot);
    }
  }
  return encoded;
}

/**
 * Create an MLP with the specified architecture.
 *
 * @param {{inputDim:number, fourierFeatures:number, hiddenLayers:number[], activation:string}} config
 * @returns {object} Network state with layers, Adam moments and scratch holders.
 */
export function createNetwork(config) {
  const { fourierFeatures, hiddenLayers } = config;
  const activation = config.activation === 'relu' ? 'relu' : 'tanh';
  const fourierOutputDim = fourierFeatures * 2;
  const layerSizes = [fourierOutputDim, ...hiddenLayers, 2]; // 2 outputs (x, y)

  const layers = [];
  for (let l = 0; l < layerSizes.length - 1; l++) {
    const fanIn = layerSizes[l];
    const fanOut = layerSizes[l + 1];
    const scale = Math.sqrt(2.0 / (fanIn + fanOut)); // Xavier
    const weights = new Float32Array(fanIn * fanOut);
    for (let i = 0; i < weights.length; i++) {
      const u1 = Math.random();
      const u2 = Math.random();
      weights[i] = scale * Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
    }
    layers.push({
      weights,
      biases: new Float32Array(fanOut),
      fanIn,
      fanOut,
      // Adam state
      mW: new Float32Array(fanIn * fanOut),
      vW: new Float32Array(fanIn * fanOut),
      mB: new Float32Array(fanOut),
      vB: new Float32Array(fanOut),
      // Preallocated gradients (sized once, reused every backward)
      dW: new Float32Array(fanIn * fanOut),
      dB: new Float32Array(fanOut),
    });
  }

  const maxFan = Math.max(...layerSizes);

  return {
    layers,
    activation,
    layerSizes,
    maxFan,
    t: 0,
    // Lazily sized scratch for the render pass (batch = particle count).
    _render: { batch: 0, buffers: null },
    // Lazily sized scratch for the training pass (batch = mini-batch size).
    _train: { batch: 0, pre: null, act: null, dA: null, dB2: null },
  };
}

/**
 * Ensure render scratch buffers exist for the given batch size.
 * @param {object} network
 * @param {number} batchSize
 */
function ensureRenderBuffers(network, batchSize) {
  const r = network._render;
  if (r.batch >= batchSize && r.buffers) return;
  const buffers = [];
  for (const layer of network.layers) {
    buffers.push(new Float32Array(batchSize * layer.fanOut));
  }
  r.batch = batchSize;
  r.buffers = buffers;
}

/**
 * Ensure training scratch buffers exist for the given batch size.
 * @param {object} network
 * @param {number} batchSize
 */
function ensureTrainBuffers(network, batchSize) {
  const tr = network._train;
  if (tr.batch >= batchSize && tr.pre) return;
  const pre = [];
  const act = [];
  for (const layer of network.layers) {
    pre.push(new Float32Array(batchSize * layer.fanOut));
    act.push(new Float32Array(batchSize * layer.fanOut));
  }
  tr.batch = batchSize;
  tr.pre = pre;
  tr.act = act;
  // Two ping-pong buffers for the back-propagated gradient wrt activations.
  tr.dA = new Float32Array(batchSize * network.maxFan);
  tr.dB2 = new Float32Array(batchSize * network.maxFan);
}

/**
 * Forward pass for rendering only (no gradient caches).
 * Writes into preallocated buffers and returns the final one. Do not mutate
 * the returned array; copy out the values you need.
 *
 * @param {object} network
 * @param {Float32Array} input Row-major [batchSize x fourierDim].
 * @param {number} batchSize
 * @returns {Float32Array} Row-major [batchSize x 2] of tanh-bounded outputs.
 */
export function forwardRender(network, input, batchSize) {
  ensureRenderBuffers(network, batchSize);
  const { layers, activation, _render } = network;
  const numLayers = layers.length;
  let current = input;

  for (let l = 0; l < numLayers; l++) {
    const { weights, biases, fanIn, fanOut } = layers[l];
    const output = _render.buffers[l];
    const isLast = l === numLayers - 1;

    for (let i = 0; i < batchSize; i++) {
      const inOff = i * fanIn;
      const outOff = i * fanOut;
      for (let j = 0; j < fanOut; j++) {
        let sum = biases[j];
        const wBase = j * fanIn;
        for (let k = 0; k < fanIn; k++) {
          sum += current[inOff + k] * weights[wBase + k];
        }
        output[outOff + j] = sum;
      }
    }

    const n = batchSize * fanOut;
    if (!isLast && activation === 'relu') {
      for (let i = 0; i < n; i++) output[i] = output[i] > 0 ? output[i] : 0;
    } else {
      for (let i = 0; i < n; i++) output[i] = Math.tanh(output[i]);
    }
    current = output;
  }

  return current;
}

/**
 * Forward + backward + Adam update on a mini-batch. Self-contained: runs its
 * own forward with gradient caches, all in preallocated buffers.
 *
 * @param {object} network
 * @param {Float32Array} trainInput Row-major [batchSize x fourierDim].
 * @param {Float32Array} targets Row-major [batchSize x 2], normalised positions.
 * @param {number} batchSize
 * @param {number} learningRate
 * @returns {number} Mean squared error over the batch.
 */
export function backward(network, trainInput, targets, batchSize, learningRate) {
  ensureTrainBuffers(network, batchSize);
  const { layers, activation, _train } = network;
  const numLayers = layers.length;
  const pre = _train.pre;
  const act = _train.act;

  // ---- Forward with caches ----
  let current = trainInput;
  for (let l = 0; l < numLayers; l++) {
    const { weights, biases, fanIn, fanOut } = layers[l];
    const preL = pre[l];
    const actL = act[l];
    const isLast = l === numLayers - 1;

    for (let i = 0; i < batchSize; i++) {
      const inOff = i * fanIn;
      const outOff = i * fanOut;
      for (let j = 0; j < fanOut; j++) {
        let sum = biases[j];
        const wBase = j * fanIn;
        for (let k = 0; k < fanIn; k++) {
          sum += current[inOff + k] * weights[wBase + k];
        }
        preL[outOff + j] = sum;
      }
    }

    const n = batchSize * fanOut;
    if (!isLast && activation === 'relu') {
      for (let i = 0; i < n; i++) actL[i] = preL[i] > 0 ? preL[i] : 0;
    } else {
      for (let i = 0; i < n; i++) actL[i] = Math.tanh(preL[i]);
    }
    current = actL;
  }

  // ---- Loss + output-layer gradient ----
  const output = act[numLayers - 1];
  const outputSize = 2;
  let totalLoss = 0;
  let dCur = _train.dA;
  for (let i = 0; i < batchSize * outputSize; i++) {
    const diff = output[i] - targets[i];
    totalLoss += diff * diff;
    dCur[i] = (2 * diff) / batchSize;
  }
  const meanLoss = totalLoss / (batchSize * outputSize);

  // Adam timestep once per call.
  network.t++;
  const bc1 = 1 - Math.pow(ADAM_BETA1, network.t);
  const bc2 = 1 - Math.pow(ADAM_BETA2, network.t);

  let dNext = _train.dB2;

  for (let l = numLayers - 1; l >= 0; l--) {
    const layer = layers[l];
    const { weights, fanIn, fanOut, dW, dB } = layer;
    const preL = pre[l];
    const inputAct = l === 0 ? trainInput : act[l - 1];
    const isLast = l === numLayers - 1;

    // Gradient through the activation, written back into dCur in place.
    if (isLast || activation !== 'relu') {
      for (let i = 0; i < batchSize * fanOut; i++) {
        const t = Math.tanh(preL[i]);
        dCur[i] *= 1 - t * t;
      }
    } else {
      for (let i = 0; i < batchSize * fanOut; i++) {
        if (preL[i] <= 0) dCur[i] = 0;
      }
    }

    // Weight and bias gradients (zero the reused buffers first).
    dW.fill(0);
    dB.fill(0);
    for (let i = 0; i < batchSize; i++) {
      const inOff = i * fanIn;
      const outOff = i * fanOut;
      for (let j = 0; j < fanOut; j++) {
        const g = dCur[outOff + j];
        dB[j] += g;
        const wBase = j * fanIn;
        for (let k = 0; k < fanIn; k++) {
          dW[wBase + k] += inputAct[inOff + k] * g;
        }
      }
    }

    // Propagate gradient to the previous layer's activations.
    if (l > 0) {
      for (let i = 0; i < batchSize; i++) {
        const inOff = i * fanIn;
        const outOff = i * fanOut;
        for (let k = 0; k < fanIn; k++) dNext[inOff + k] = 0;
        for (let j = 0; j < fanOut; j++) {
          const dpj = dCur[outOff + j];
          const wBase = j * fanIn;
          for (let k = 0; k < fanIn; k++) {
            dNext[inOff + k] += weights[wBase + k] * dpj;
          }
        }
      }
      // Swap ping-pong buffers: dNext becomes the incoming gradient next iter.
      const tmp = dCur;
      dCur = dNext;
      dNext = tmp;
    }

    // Adam update for this layer.
    const { mW, vW, mB, vB, biases } = layer;
    for (let i = 0; i < dW.length; i++) {
      mW[i] = ADAM_BETA1 * mW[i] + (1 - ADAM_BETA1) * dW[i];
      vW[i] = ADAM_BETA2 * vW[i] + (1 - ADAM_BETA2) * dW[i] * dW[i];
      const mHat = mW[i] / bc1;
      const vHat = vW[i] / bc2;
      weights[i] -= (learningRate * mHat) / (Math.sqrt(vHat) + ADAM_EPS);
    }
    for (let i = 0; i < dB.length; i++) {
      mB[i] = ADAM_BETA1 * mB[i] + (1 - ADAM_BETA1) * dB[i];
      vB[i] = ADAM_BETA2 * vB[i] + (1 - ADAM_BETA2) * dB[i] * dB[i];
      const mHat = mB[i] / bc1;
      const vHat = vB[i] / bc2;
      biases[i] -= (learningRate * mHat) / (Math.sqrt(vHat) + ADAM_EPS);
    }
  }

  return meanLoss;
}