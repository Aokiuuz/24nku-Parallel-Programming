#include <cstddef>

constexpr std::size_t N = 1u << 18;

alignas(64) static double g_data[N];

void init_data() {
    for (std::size_t i = 0; i < N; ++i) {
        g_data[i] = 1.0 / static_cast<double>((i % 251) + 1);
    }
}

double sum_unroll4() {
    double sum0 = 0.0;
    double sum1 = 0.0;
    double sum2 = 0.0;
    double sum3 = 0.0;
    std::size_t i = 0;
    for (; i + 3 < N; i += 4) {
        sum0 += g_data[i];
        sum1 += g_data[i + 1];
        sum2 += g_data[i + 2];
        sum3 += g_data[i + 3];
    }
    for (; i < N; ++i) {
        sum0 += g_data[i];
    }
    return (sum0 + sum1) + (sum2 + sum3);
}

int main() {
    init_data();
    volatile double sink = sum_unroll4();
    return static_cast<int>(sink);
}
