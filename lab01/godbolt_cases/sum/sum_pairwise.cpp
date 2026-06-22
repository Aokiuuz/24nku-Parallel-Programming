#include <cstddef>

constexpr std::size_t N = 1u << 18;

alignas(64) static double g_data[N];
alignas(64) static double g_work[N];

void init_data() {
    for (std::size_t i = 0; i < N; ++i) {
        g_data[i] = 1.0 / static_cast<double>((i % 251) + 1);
        g_work[i] = g_data[i];
    }
}

double sum_pairwise() {
    std::size_t m = N;
    while (m > 1) {
        std::size_t write = 0;
        std::size_t i = 0;
        for (; i + 1 < m; i += 2) {
            g_work[write++] = g_work[i] + g_work[i + 1];
        }
        if (i < m) {
            g_work[write++] = g_work[i];
        }
        m = write;
    }
    return g_work[0];
}

int main() {
    init_data();
    volatile double sink = sum_pairwise();
    return static_cast<int>(sink);
}
