// LPF.h
#ifndef LPF_H
#define LPF_H

#include <stddef.h>
#include <math.h>
// N = number of stages
template <size_t N>
class LPF {
public:
    // K = not time-constant, ts = sample-time
    LPF(float K, float ts)
      : a(exp(-ts / K))
      , b(1.0f - a)
    {
        // zero-initialize all stages
        for (size_t i = 0; i < N; ++i) y[i] = 0.0f;
    }

    float update(float u) {
        float v = u;
        for (size_t k = 0; k < N; ++k) {
            y[k] = a * y[k] + b * v;
            v    = y[k];
        }
        return v;
    }

private:
    float a, b;
    float y[N];
};

#endif // LPF_H
