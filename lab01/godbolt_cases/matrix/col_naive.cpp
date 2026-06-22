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

void col_naive() {
    for (std::size_t i = 0; i < N; ++i) {
        double acc = 0.0;
        for (std::size_t j = 0; j < N; ++j) {
            acc += g_matrix[idx(j, i)] * g_vec[j];
        }
        g_out[i] = acc;
    }
}

int main() {
    init_data();
    col_naive();
    return static_cast<int>(g_out[0]);
}
