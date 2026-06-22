#include <cstddef>

constexpr std::size_t N = 1u << 18;

alignas(64) static double g_data[N];

void init_data() {
    for (std::size_t i = 0; i < N; ++i) {
        g_data[i] = 1.0 / static_cast<double>((i % 251) + 1);
    }
}

double sum_naive() {
    double sum = 0.0;
    for (std::size_t i = 0; i < N; ++i) {
        sum += g_data[i];
    }
    return sum;
}

int main() {
    init_data();
    volatile double sink = sum_naive();
    return static_cast<int>(sink);
}
