#!/usr/bin/python

from collections import namedtuple
import random
import numpy
from numpy import array, sum, mean, std
from numpy.random import random_sample, randint, poisson
import ghmm
from matplotlib import pyplot as pl

Model = namedtuple('Model', 'n_states n_obs start_prob trans_prob emissions')

def weighted_choice(choices, probs):
        #assert sum(probs) == 1
        r = random.random()
        for c,p in zip(choices, probs):
                if r < p: return c
                r -= p
        raise RuntimeError()

def random_model(n_states, n_obs):
        """ Create a ranodm model with the given number of states and observables """
        emissions = randint(0, 1500, (n_states, n_obs))
        return random_model_from_emissions(emissions)

def random_model_from_emissions(emissions):
        """ Create a random model using a given set of emission parameters.
            emissions should be an MxN matrix (M=number of states, N=number of observables) """
        if len(emissions.shape) == 1:
                emissions = emissions.reshape((len(emissions), 1))
        n_states, n_obs = emissions.shape
        start_prob = random_sample(n_states)
        start_prob /= sum(start_prob)

        transition_prob = []
        for i in xrange(n_states):
                stay_prob = random.random()
                t = stay_prob * random_sample(n_states)
                t[i] = stay_prob
                t /= sum(t)
                transition_prob.append(t)

        transition_prob = array(transition_prob)
        return Model(n_states, n_obs, start_prob, transition_prob, emissions)

def random_data(model, length, noise=True):
        """ Generate emissions data from the given model.
            Returns:
                    data: Emission stream
                    state_seq: Sequence of states
                    dwells: A list of lists of dwell times
        """
        state_seq = []
        state = weighted_choice(xrange(model.n_states), model.start_prob)
        data = []
        dwells = [ [] for s in range(model.n_states) ]
        dwell = 0
        for i in xrange(length):
                state_seq.append(state)
                datum = model.emissions[state]
                if noise:
                        datum = poisson(datum) 
                data.append(datum)

                old_state = state
                state = weighted_choice(xrange(model.n_states), model.trans_prob[state])

                if state != old_state:
                        dwells[old_state].append(dwell)
                        dwell = 0
                
                dwell += 1


        return data, state_seq, dwells

def transition_matrix(hmm):
        """ Get the transition matrix from a ghmm.HMM as a numpy array """
        get_row = lambda row : [ hmm.getTransition(row,col) for col in range(hmm.N) ]
        return array([ get_row(row) for row in range(hmm.N) ])

# Generate a model to pull data from
n_states = 6
emissions = array([ 342, 541, 280, 844, 772, 300 ])
model = random_model_from_emissions(emissions)
print "Model:"
print model.trans_prob[0,:]

# Generate a data set with which to track our convergence
# This will not be learned from, only tested for likelihood
data, seq, dwells = random_data(model, 100000)
dom = ghmm.IntegerRange(0,10000)
distr = ghmm.DiscreteDistribution(dom)
test_data = ghmm.EmissionSequence(dom, data)

# Plot a sample of data
if True:
        pl.plot(data)
        pl.plot(seq)
        pl.savefig('model-photons.png')
        pl.clf()

# Plot bin count distribution
if True:
        pl.suptitle("Original Model (Bin Count)")
        pl.hist(data, 100)
        text = "States:\n" + '\n'.join( ['%d:  %d' % i for i in enumerate(model.emissions)] )
        pl.figtext(0.8, 0.6, text)
        pl.figtext(0.3, 0.6, numpy.array_str(model.trans_prob, precision=2))
        pl.savefig('model-bins.png')
        pl.clf()

if True:
        for i in range(n_states):
                pl.suptitle("Original Model (FPT)")
                pl.hist(dwells[i], 100)
                pl.savefig('model-dwells-state%d.png' % i)
                pl.clf()


# Try teaching several randomly initialized models
print
print "Learn:"
numpy.set_printoptions(suppress=True)
for i in range(5):
        # Setup HMM with a new random model
        new = random_model(n_states, 1)
        B = [ [float(e[0]), float(e[0])] for e in model.emissions[0:n_states] ]  # mu, sigma
        hmm = ghmm.HMMFromMatrices(dom, distr, new.trans_prob, B, new.start_prob)

        if True:
                data = hmm.sampleSingle(100000)
                print data.getStateLabel()
                pl.suptitle("Initial Model %d" % i)
                pl.hist(data, 100)
                text = "States:\n" + '\n'.join( ['%d:  %d' % (j, hmm.getEmission(j)[0]) for j in range(n_states)] )
                pl.figtext(0.8, 0.6, text)
                pl.figtext(0.3, 0.6, numpy.array_str(transition_matrix(hmm), precision=2))
                pl.figtext(0.3, 0.5, "Test Likelihood: %e" % hmm.loglikelihoods(test_data)[0])
                pl.savefig('initial-%d.png' % i)
                pl.clf()

        # Training iterations
        for j in range(10):
                data, seq, dwells = random_data(model, 100000)
                seq = ghmm.EmissionSequence(dom, data)
                hmm.baumWelch(seq, 50, 0.1)

        if True:
                data = hmm.sampleSingle(100000)
                pl.suptitle("Trained Model %d" % i)
                pl.hist(data, 100)
                text = "States:\n" + '\n'.join( ['%d:  %d' % (j, hmm.getEmission(j)[0]) for j in range(n_states)] )
                pl.figtext(0.8, 0.6, text)
                pl.figtext(0.3, 0.6, numpy.array_str(transition_matrix(hmm), precision=2))
                pl.figtext(0.3, 0.5, "Test Likelihood: %e" % hmm.loglikelihoods(test_data)[0])
                pl.savefig('trained%d-bins.png' % i)
                pl.clf()

