import torch
import torch.nn as nn
import numpy as np

from lif.lif_neuron_group import LIFNeuronGroup

class LIFLayer(nn.Module):
    """
    A PyTorch wrapper for the LIFNeuronGroup class to integrate with PyTorch layers.
    """
    def __init__(self,
                 num_neurons,
                 V_th=1.0,
                 V_reset=0.0,
                 tau=20.0,
                 dt=1.0,
                 eta=0.1,
                 use_adaptive_threshold=True,
                 noise_std=0.1,
                 stochastic=True,
                 min_threshold=0.5,
                 max_threshold=2.0,
                 batch_size=1,
                 device="cuda",
                 spike_coding=None,
                 surrogate_gradient_function="heaviside",
                 alpha=1.0,
                 allow_dynamic_spike_probability=False,
                 base_alpha=2.0,
                 tau_adapt=20.0,
                 neuromod_transform=None):
        """
        :param num_neurons: Number of neurons in the group.
        :param V_th: Initial threshold voltage for all neurons.
        :param V_reset: Reset voltage after a spike.
        :param tau: Membrane time constant, controlling decay rate.
        :param dt: Time step for updating the membrane potential.
        :param eta: Adaptation rate for the threshold voltage.
        :param noise_std: Standard deviation of Gaussian noise added to the membrane potential.
        :param stochastic: Whether to enable stochastic firing.
        :param min_threshold: Minimum threshold value.
        :param max_threshold: Maximum threshold value.
        :param batch_size: Batch size for the input data.
        :param device: Device to run the simulation on.
        :param spike_coding: (Optional) Spike coding scheme.
        :param surrogate_gradient_function: Surrogate gradient function for backpropagation.
        :param alpha: Parameter for the surrogate gradient function.
        :param allow_dynamic_spike_probability: Whether to allow dynamic spike probability (uses internal state).
        :param base_alpha: Base alpha value for the dynamic sigmoid function.
        :param tau_adapt: Time constant for adaptation (used in dynamic spike probability).
        :param neuromod_transform: A function or module that transforms an external modulation tensor
                                   (e.g., reward/error signal) into modulation factors.
                                   If None, a default sigmoid transformation will be applied.
        """
        super(LIFLayer, self).__init__()

        self.lif_group = LIFNeuronGroup(
            num_neurons=num_neurons,
            V_th=V_th,
            V_reset=V_reset,
            tau=tau,
            dt=dt,
            eta=eta,
            use_adaptive_threshold=use_adaptive_threshold,
            noise_std=noise_std,
            stochastic=stochastic,
            min_threshold=min_threshold,
            max_threshold=max_threshold,
            batch_size=batch_size,
            device=device,
            surrogate_gradient_function=surrogate_gradient_function,
            alpha=alpha,
            allow_dynamic_spike_probability=allow_dynamic_spike_probability,
            base_alpha=base_alpha,
            tau_adapt=tau_adapt,
            neuromod_transform=neuromod_transform
        )
        self.spike_coding = spike_coding

    def forward(self, input_data: torch.Tensor, external_modulation: torch.Tensor = None) -> torch.Tensor:
        """
        Forward pass for the LIFNeuronGroup in PyTorch.

        :param input_data: Input tensor of shape (batch_size, num_neurons) or
                           (timesteps, batch_size, num_neurons).
        :param external_modulation: External modulation tensor (e.g., reward signal)
                                    with shape (batch_size, num_neurons) or broadcastable shape.
        :return: Spike tensor (binary) of shape (batch_size, num_neurons) or
                 (timesteps, batch_size, num_neurons).
        """
        self.lif_group.reset_state()

        # If input_data includes a time dimension.
        if len(input_data.shape) == 3:
            timesteps, batch_size, num_neurons = input_data.shape
            assert batch_size == self.lif_group.batch_size, \
                f"Batch size must match ({self.lif_group.batch_size})."
            assert num_neurons == self.lif_group.num_neurons, \
                f"Number of neurons must match ({self.lif_group.num_neurons})."

            output_spikes = []
            for t in range(timesteps):
                spikes = self.lif_group.step(input_data[t], external_modulation=external_modulation)
                output_spikes.append(spikes)
            return torch.stack(output_spikes, dim=0)
        else:
            assert input_data.shape == (self.lif_group.batch_size, self.lif_group.num_neurons), \
                f"Input tensor shape must match (batch_size={self.lif_group.batch_size}, num_neurons={self.lif_group.num_neurons})."
            return self.lif_group.step(input_data, external_modulation=external_modulation)
