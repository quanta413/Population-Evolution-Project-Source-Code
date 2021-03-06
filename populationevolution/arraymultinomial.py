# -*- coding: utf-8 -*-
"""
Created on Wed Sep 12 16:40:28 2018

@author: nashere2
"""

import numpy as np


def check(N, Pis):
    if not np.all(Pis >= 0):
            raise ValueError('All probabilities must be 0 or positive.')
    total_probability = np.sum(Pis, axis=0)
    if not np.all(np.isclose(total_probability, 1., rtol=0, atol=1e-13)):
        raise ValueError('The total probability parameters of a'
                         ' multinomial distribution must sum to 1.')
    if Pis.shape[1:] != N.shape:
        raise AttributeError('Pis must be the shape of N plus '
                             'one additional axis in the lead')


def array_multinomial(N_array, Pis_array, checks=True):
    """
    Draw from multinomial distribution P(x1, x2,..., xi; N, p1, p2, ... pi)
    array wise where N's are from N_array and their respective pi's are from
    Pis_array with matching trailing indices and the leading index is the
    value of i.

    Return an array of xis in the same shape as the array Pis_array.

    The last subarray along the leading axis of Pis_array is ignored if checks
    is False because it is assumed to be equal to 1 minus the rest of that axis
    since probability is conserved. If checks is True then we check to make
    sure all sums over pi's are equal to 1 as required.
    """

    if checks is True:
        N_array = np.array(N_array)
        Pis_array = np.array(Pis_array)
        check(N_array, Pis_array)

    Xis_array = np.empty_like(Pis_array, dtype='int32')
    N_remain_array = np.copy(N_array)
    prob_remain = np.ones_like(N_array, dtype='float64')
    for i in range(Pis_array.shape[0]-1):
        Xis_array[i, ...] = np.random.binomial(N_remain_array,
                                               Pis_array[i, ...]/prob_remain)
        N_remain_array -= Xis_array[i, ...]
        prob_remain -= Pis_array[i, ...]
    Xis_array[-1, ...] = N_remain_array
    return Xis_array


def approximate_binomial(N, P):
    """
    Run binomial draws for very large N by using the poisson or normal
    approximation depending which is appropriate.

    Should be identical to calling np.random.binomial with size=None for
    integers less than 32 bits.
    """
    N_below_32bit = N * (N <= 2 * 10**9)
    N_above_32bit = N - N_below_32bit
    draw_below = np.random.binomial(N_below_32bit.astype('int32'), P)
    N_broadcast, P_broadcast = np.broadcast_arrays(N_above_32bit, P)
    NP = N_broadcast*P_broadcast
    poisson_approx_segment = NP < 100
    draw_poisson = np.random.poisson(NP*poisson_approx_segment)
    N_normal_approx = N_broadcast * (1 - poisson_approx_segment)
    normal_std = np.sqrt(N_normal_approx * P_broadcast * (1 - P_broadcast))
    draw_normal = np.int64(np.random.normal(N_normal_approx*P_broadcast,
                                            normal_std))
    return draw_below + draw_poisson + draw_normal


def array_multinomial_int64(N_array, Pis_array, checks=True):
    """
    Same as array_multinomial function except it can handle 64 bit integer
    inputs in N_array.
    """

    if checks is True:
        N_array = np.array(N_array)
        Pis_array = np.array(Pis_array)
        check(N_array, Pis_array)

    Xis_array = np.empty_like(Pis_array, dtype='int64')
    N_remain_array = np.copy(N_array)
    prob_remain = np.ones_like(N_array, dtype='float64')
    for i in range(Pis_array.shape[0]-1):
        Xis_array[i, ...] = approximate_binomial(N_remain_array,
                                                 Pis_array[i, ...]/prob_remain)
        N_remain_array -= Xis_array[i, ...]
        prob_remain -= Pis_array[i, ...]
    Xis_array[-1, ...] = N_remain_array
    return Xis_array


def multinomial_int64(N, Pis, checks=True):
    '''Replacement for the numpy multinomial function that works even when
    N exceeds 10^9.

    Not for use if N is an array.'''
    if checks:
        N_array = np.array(N)
        Pis = np.array(Pis)
        check(N_array, Pis)

    # if N is less than the cutoff above which numpy.random.multinomial fails
    # just call np.random.multinomial
    if N <= 10**9:
        return np.random.multinomial(N, Pis)

    return_array = np.empty_like(Pis, dtype='int64')
    sort_order = np.argsort(Pis)
    Pis = Pis[sort_order]
    cumulative = np.cumsum(Pis)

    li = 0
    try:
        ri = np.where(N*cumulative <= 10**9)[0][-1]
        p_cut = cumulative[ri]
        if ri > li:
            chunk_small = True
        else:
            chunk_small = False
    except IndexError:
        chunk_small = False
    N_remaining = N

    while chunk_small:
        mean = N_remaining*p_cut
        std = np.sqrt(np.maximum(0, mean*(1-p_cut)))
        N_left = np.int64(np.random.normal(mean, std))
        N_remaining = N_remaining - N_left
        return_array[li:ri+1] = np.random.multinomial(N_left,
                                                      Pis[li:ri+1]/p_cut)
        li = ri+1
        cumulative = cumulative - p_cut
        if li >= Pis.size:
            return return_array[np.argsort(sort_order)]
        try:
            ri = np.where(N_remaining*cumulative <= 10**9)[0][-1]
            p_cut = cumulative[ri]
            if ri <= li:
                break
        except IndexError:
            break

    p_remaining = cumulative[-1]
    for i in range(li, Pis.size-1):
        mean = N_remaining*Pis[i]/p_remaining
        std = np.sqrt(np.maximum(0, mean*(1-Pis[i]/p_remaining)))
        left_N = np.int64(np.random.normal(mean, std))
        N_remaining = N_remaining - left_N
        p_remaining = p_remaining - Pis[i]
        return_array[i] = left_N
    return_array[-1] = N_remaining

    return return_array[np.argsort(sort_order)]
