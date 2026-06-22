#include <cstddef>

constexpr std::size_t N = 1u << 18;

alignas(64) static double g_data[N];

void init_data() {
    for (std::size_t i = 0; i < N; ++i) {
        g_data[i] = 1.0 / static_cast<double>((i % 251) + 1);
    }
}

double sum_dual() {
    double sum0 = 0.0;
    double sum1 = 0.0;
    std::size_t i = 0;
    for (; i + 1 < N; i += 2) {
        sum0 += g_data[i];
        sum1 += g_data[i + 1];
    }
    for (; i < N; ++i) {
        sum0 += g_data[i];
    }
    return sum0 + sum1;
}

int main() {
    init_data();
    volatile double sink = sum_dual();
    return static_cast<int>(sink);
}
