#include <cstddef>

constexpr std::size_t N = 1024;

alignas(64) static double g_matrix[N * N];
alignas(64) static double g_vec[N];
alignas(64) static double g_out[N];

static inline std::size_t idx(std::size_t row, std::size_t col) {
    return row * N + col;
}

void init_data() {
    for (std::size_t i = 0; i < N; ++i) {
        g_vec[i] = static_cast<double>((i % 97) + 1) * 0.25;
        g_out[i] = 0.0;
        for (std::size_t j = 0; j < N; ++j) {
            g_matrix[idx(i, j)] = static_cast<double>((i + j) % 113);
        }
    }
}

void row_cache() {
    for (std::size_t i = 0; i < N; ++i) {
        g_out[i] = 0.0;
    }
    for (std::size_t j = 0; j < N; ++j) {
        const double aj = g_vec[j];
        const std::size_t base = j * N;
        for (std::size_t i = 0; i < N; ++i) {
            g_out[i] += g_matrix[base + i] * aj;
        }
    }
}

int main() {
    init_data();
    row_cache();
    return static_cast<int>(g_out[0]);
}
