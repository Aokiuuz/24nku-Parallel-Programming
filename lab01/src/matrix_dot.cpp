#include "common.hpp"

#include <algorithm>
#include <cstdlib>

using Matrix = std::vector<double>;
using Vector = std::vector<double>;

static inline std::size_t idx(std::size_t row, std::size_t col, std::size_t n) {
    return row * n + col;
}

Vector make_vector(std::size_t n) {
    Vector a(n);
    for (std::size_t i = 0; i < n; ++i) {
        a[i] = static_cast<double>((i % 97) + 1) * 0.25;
    }
    return a;
}

Matrix make_matrix(std::size_t n) {
    Matrix b(n * n);
    for (std::size_t i = 0; i < n; ++i) {
        for (std::size_t j = 0; j < n; ++j) {
            b[idx(i, j, n)] = static_cast<double>((i + j) % 113);
        }
    }
    return b;
}

void col_naive(const Matrix& b, const Vector& a, Vector& sum, std::size_t n) {
    for (std::size_t i = 0; i < n; ++i) {
        double acc = 0.0;
        for (std::size_t j = 0; j < n; ++j) {
            acc += b[idx(j, i, n)] * a[j];
        }
        sum[i] = acc;
    }
}

void row_cache(const Matrix& b, const Vector& a, Vector& sum, std::size_t n) {
    std::fill(sum.begin(), sum.end(), 0.0);
    for (std::size_t j = 0; j < n; ++j) {
        const double aj = a[j];
        const std::size_t base = j * n;
        for (std::size_t i = 0; i < n; ++i) {
            sum[i] += b[base + i] * aj;
        }
    }
}

void row_cache_unroll4(const Matrix& b, const Vector& a, Vector& sum, std::size_t n) {
    std::fill(sum.begin(), sum.end(), 0.0);
    for (std::size_t j = 0; j < n; ++j) {
        const double aj = a[j];
        const std::size_t base = j * n;
        std::size_t i = 0;
        for (; i + 3 < n; i += 4) {
            sum[i] += b[base + i] * aj;
            sum[i + 1] += b[base + i + 1] * aj;
            sum[i + 2] += b[base + i + 2] * aj;
            sum[i + 3] += b[base + i + 3] * aj;
        }
        for (; i < n; ++i) {
            sum[i] += b[base + i] * aj;
        }
    }
}

bool verify_same(const Vector& lhs, const Vector& rhs) {
    for (std::size_t i = 0; i < lhs.size(); ++i) {
        if (!almost_equal(lhs[i], rhs[i])) {
            std::cerr << "mismatch at " << i << ": " << lhs[i] << " vs " << rhs[i] << '\n';
            return false;
        }
    }
    return true;
}

int estimate_repeat(std::size_t n) {
    if (n <= 128) return 400;
    if (n <= 256) return 120;
    if (n <= 512) return 30;
    if (n <= 1024) return 8;
    return 3;
}

int main(int argc, char** argv) {
    std::vector<std::size_t> sizes = {128, 256, 512, 1024};
    if (argc > 1) {
        sizes.clear();
        for (int i = 1; i < argc; ++i) {
            sizes.push_back(static_cast<std::size_t>(std::strtoull(argv[i], nullptr, 10)));
        }
    }

    print_table_header("matrix column dot product");
    for (std::size_t n : sizes) {
        const Matrix b = make_matrix(n);
        const Vector a = make_vector(n);
        Vector out_naive(n), out_cache(n), out_unroll(n);

        col_naive(b, a, out_naive, n);
        row_cache(b, a, out_cache, n);
        row_cache_unroll4(b, a, out_unroll, n);
        if (!verify_same(out_naive, out_cache) || !verify_same(out_naive, out_unroll)) {
            return 1;
        }

        const int repeat = estimate_repeat(n);
        const double t_naive = benchmark([&] { col_naive(b, a, out_naive, n); }, repeat);
        const double t_cache = benchmark([&] { row_cache(b, a, out_cache, n); }, repeat);
        const double t_unroll = benchmark([&] { row_cache_unroll4(b, a, out_unroll, n); }, repeat);

        print_table_row("col_naive", n, repeat, t_naive, 1.0);
        print_table_row("row_cache", n, repeat, t_cache, t_naive / t_cache);
        print_table_row("row_cache_u4", n, repeat, t_unroll, t_naive / t_unroll);
    }
    return 0;
}
