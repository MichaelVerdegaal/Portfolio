/**
 * Neural network module: MLP with Random Fourier Features and Adam optimiser.
 * Hand-written forward pass and backpropagation — no ML libraries.
 * Uses Float32Array for performance in browser tight loops.
 */

/**
 * Create a random matrix for Fourier feature encoding.
 * Projects input_dim -> num_frequencies, then sin/cos gives 2*num_frequencies features.
 */
export function createFourierMatrix(inputDim, numFrequencies) {
  // Sample from normal distribution, scaled for good frequency coverage
  const scale = 8.0;
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
 * inputs: Float32Array [batchSize × inputDim], row-major
 * Returns Float32Array [batchSize × (numFrequencies * 2)]
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
 */
export function createNetwork(config) {
  const { inputDim, fourierFeatures, hiddenLayers, activation } = config;
  const fourierOutputDim = fourierFeatures * 2;
  const layerSizes = [fourierOutputDim, ...hiddenLayers, 2]; // 2 outputs (x, y)

  const layers = [];
  for (let l = 0; l < layerSizes.length - 1; l++) {
    const fanIn = layerSizes[l];
    const fanOut = layerSizes[l + 1];
    // Xavier initialization
    const scale = Math.sqrt(2.0 / (fanIn + fanOut));
    const weights = new Float32Array(fanIn * fanOut);
    const biases = new Float32Array(fanOut);
    for (let i = 0; i < weights.length; i++) {
      const u1 = Math.random();
      const u2 = Math.random();
      weights[i] = scale * Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
    }

    layers.push({
      weights,
      biases,
      fanIn,
      fanOut,
      // Adam state
      mW: new Float32Array(fanIn * fanOut),
      vW: new Float32Array(fanIn * fanOut),
      mB: new Float32Array(fanOut),
      vB: new Float32Array(fanOut),
    });
  }

  return { layers, activation, layerSizes, t: 0 };
}

/**
 * Forward pass (render-only, no gradient storage needed).
 * Returns Float32Array [batchSize × 2] of tanh-bounded outputs.
 */
export function forwardRender(network, input, batchSize) {
  const { layers, activation } = network;
  let current = input;
  const numLayers = layers.length;

  for (let l = 0; l < numLayers; l++) {
    const { weights, biases, fanIn, fanOut } = layers[l];
    const output = new Float32Array(batchSize * fanOut);

    for (let i = 0; i < batchSize; i++) {
      const inOff = i * fanIn;
      const outOff = i * fanOut;
      for (let j = 0; j < fanOut; j++) {
        let sum = biases[j];
        for (let k = 0; k < fanIn; k++) {
          sum += current[inOff + k] * weights[k * fanOut + j];
        }
        output[outOff + j] = sum;
      }
    }

    // Activation
    if (l < numLayers - 1) {
      if (activation === 'relu') {
        for (let i = 0; i < output.length; i++) {
          output[i] = output[i] > 0 ? output[i] : 0;
        }
      } else {
        for (let i = 0; i < output.length; i++) {
          output[i] = Math.tanh(output[i]);
        }
      }
    } else {
      // Last layer always uses tanh for bounded output
      for (let i = 0; i < output.length; i++) {
        output[i] = Math.tanh(output[i]);
      }
    }
    current = output;
  }

  return current;
}

/**
 * Forward pass with gradient storage for backprop.
 * Returns { output, activations, preActivations }.
 */
export function forward(network, input, batchSize) {
  const { layers, activation } = network;
  const activations = [input];
  const preActivations = [];
  let current = input;
  const numLayers = layers.length;

  for (let l = 0; l < numLayers; l++) {
    const { weights, biases, fanIn, fanOut } = layers[l];
    const pre = new Float32Array(batchSize * fanOut);

    for (let i = 0; i < batchSize; i++) {
      const inOff = i * fanIn;
      const outOff = i * fanOut;
      for (let j = 0; j < fanOut; j++) {
        let sum = biases[j];
        for (let k = 0; k < fanIn; k++) {
          sum += current[inOff + k] * weights[k * fanOut + j];
        }
        pre[outOff + j] = sum;
      }
    }

    preActivations.push(pre);

    const activated = new Float32Array(pre.length);
    if (l < numLayers - 1) {
      if (activation === 'relu') {
        for (let i = 0; i < pre.length; i++) {
          activated[i] = pre[i] > 0 ? pre[i] : 0;
        }
      } else {
        for (let i = 0; i < pre.length; i++) {
          activated[i] = Math.tanh(pre[i]);
        }
      }
    } else {
      for (let i = 0; i < pre.length; i++) {
        activated[i] = Math.tanh(pre[i]);
      }
    }

    activations.push(activated);
    current = activated;
  }

  return { output: current, activations, preActivations };
}

/**
 * Backward pass + Adam update.
 * trainInput: Float32Array [batchSize × fourierDim] (Fourier-encoded subset)
 * targets: Float32Array [batchSize × 2] (normalised target positions for the subset)
 * Returns mean loss.
 */
export function backward(network, trainInput, targets, batchSize, learningRate) {
  const { layers, activation } = network;
  const numLayers = layers.length;

  // Forward pass on training batch (with gradient storage)
  const { output, activations, preActivations } = forward(network, trainInput, batchSize);

  // Compute MSE loss gradient
  const outputSize = 2;
  let totalLoss = 0;
  let dActivated = new Float32Array(batchSize * outputSize);

  for (let i = 0; i < batchSize * outputSize; i++) {
    const diff = output[i] - targets[i];
    totalLoss += diff * diff;
    dActivated[i] = (2 * diff) / batchSize;
  }
  const meanLoss = totalLoss / (batchSize * outputSize);

  // Increment Adam timestep ONCE per backward call
  network.t++;
  const beta1 = 0.9;
  const beta2 = 0.999;
  const eps = 1e-8;
  const bc1 = 1 - Math.pow(beta1, network.t);
  const bc2 = 1 - Math.pow(beta2, network.t);

  // Backprop through layers
  for (let l = numLayers - 1; l >= 0; l--) {
    const { weights, biases, fanIn, fanOut } = layers[l];
    const preAct = preActivations[l];
    const inputAct = activations[l];

    // Gradient through activation
    const dPre = new Float32Array(batchSize * fanOut);
    if (l === numLayers - 1) {
      for (let i = 0; i < batchSize * fanOut; i++) {
        const t = Math.tanh(preAct[i]);
        dPre[i] = dActivated[i] * (1 - t * t);
      }
    } else if (activation === 'relu') {
      for (let i = 0; i < batchSize * fanOut; i++) {
        dPre[i] = preAct[i] > 0 ? dActivated[i] : 0;
      }
    } else {
      for (let i = 0; i < batchSize * fanOut; i++) {
        const t = Math.tanh(preAct[i]);
        dPre[i] = dActivated[i] * (1 - t * t);
      }
    }

    // Weight and bias gradients
    const dW = new Float32Array(fanIn * fanOut);
    const dB = new Float32Array(fanOut);

    for (let i = 0; i < batchSize; i++) {
      const inOff = i * fanIn;
      const outOff = i * fanOut;
      for (let j = 0; j < fanOut; j++) {
        const g = dPre[outOff + j];
        dB[j] += g;
        for (let k = 0; k < fanIn; k++) {
          dW[k * fanOut + j] += inputAct[inOff + k] * g;
        }
      }
    }

    // Propagate gradient to previous layer
    if (l > 0) {
      dActivated = new Float32Array(batchSize * fanIn);
      for (let i = 0; i < batchSize; i++) {
        const inOff = i * fanIn;
        const outOff = i * fanOut;
        for (let k = 0; k < fanIn; k++) {
          let sum = 0;
          for (let j = 0; j < fanOut; j++) {
            sum += weights[k * fanOut + j] * dPre[outOff + j];
          }
          dActivated[inOff + k] = sum;
        }
      }
    }

    // Adam update for this layer
    const layer = layers[l];
    for (let i = 0; i < dW.length; i++) {
      layer.mW[i] = beta1 * layer.mW[i] + (1 - beta1) * dW[i];
      layer.vW[i] = beta2 * layer.vW[i] + (1 - beta2) * dW[i] * dW[i];
      const mHat = layer.mW[i] / bc1;
      const vHat = layer.vW[i] / bc2;
      layer.weights[i] -= learningRate * mHat / (Math.sqrt(vHat) + eps);
    }

    for (let i = 0; i < dB.length; i++) {
      layer.mB[i] = beta1 * layer.mB[i] + (1 - beta1) * dB[i];
      layer.vB[i] = beta2 * layer.vB[i] + (1 - beta2) * dB[i] * dB[i];
      const mHat = layer.mB[i] / bc1;
      const vHat = layer.vB[i] / bc2;
      layer.biases[i] -= learningRate * mHat / (Math.sqrt(vHat) + eps);
    }
  }

  return meanLoss;
}
