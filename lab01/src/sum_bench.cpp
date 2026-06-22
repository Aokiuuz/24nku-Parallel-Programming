#include "common.hpp"

#include <algorithm>
#include <cstdlib>

using Vector = std::vector<double>;

Vector make_data(std::size_t n) {
    Vector a(n);
    for (std::size_t i = 0; i < n; ++i) {
        a[i] = 1.0 / static_cast<double>((i % 251) + 1);
    }
    return a;
}

double sum_naive(const Vector& a) {
    double sum = 0.0;
    for (double v : a) {
        sum += v;
    }
    return sum;
}

double sum_dual(const Vector& a) {
    double sum0 = 0.0;
    double sum1 = 0.0;
    std::size_t i = 0;
    for (; i + 1 < a.size(); i += 2) {
        sum0 += a[i];
        sum1 += a[i + 1];
    }
    for (; i < a.size(); ++i) {
        sum0 += a[i];
    }
    return sum0 + sum1;
}

double sum_unroll4(const Vector& a) {
    double sum0 = 0.0;
    double sum1 = 0.0;
    double sum2 = 0.0;
    double sum3 = 0.0;
    std::size_t i = 0;
    for (; i + 3 < a.size(); i += 4) {
        sum0 += a[i];
        sum1 += a[i + 1];
        sum2 += a[i + 2];
        sum3 += a[i + 3];
    }
    for (; i < a.size(); ++i) {
        sum0 += a[i];
    }
    return (sum0 + sum1) + (sum2 + sum3);
}

double sum_pairwise(Vector data) {
    std::size_t m = data.size();
    while (m > 1) {
        std::size_t write = 0;
        std::size_t i = 0;
        for (; i + 1 < m; i += 2) {
            data[write++] = data[i] + data[i + 1];
        }
        if (i < m) {
            data[write++] = data[i];
        }
        m = write;
    }
    return data.empty() ? 0.0 : data[0];
}

int estimate_repeat(std::size_t n) {
    if (n <= (1u << 12)) return 20000;
    if (n <= (1u << 16)) return 4000;
    if (n <= (1u << 20)) return 600;
    return 80;
}

int main(int argc, char** argv) {
    std::vector<std::size_t> sizes = {1u << 10, 1u << 14, 1u << 18, 1u << 22};
    if (argc > 1) {
        sizes.clear();
        for (int i = 1; i < argc; ++i) {
            sizes.push_back(static_cast<std::size_t>(std::strtoull(argv[i], nullptr, 10)));
        }
    }

    print_table_header("sum n numbers");
    for (std::size_t n : sizes) {
        const Vector a = make_data(n);
        const double ref = sum_naive(a);
        const double dual = sum_dual(a);
        const double unroll = sum_unroll4(a);
        const double pairwise = sum_pairwise(a);

        if (!almost_equal(ref, dual) || !almost_equal(ref, unroll) || !almost_equal(ref, pairwise, 1e-7)) {
            std::cerr << "verification failed at n=" << n << '\n';
            return 1;
        }

        volatile double sink = 0.0;
        const int repeat = estimate_repeat(n);

        const double t_naive = benchmark([&] { sink += sum_naive(a); }, repeat);
        const double t_dual = benchmark([&] { sink += sum_dual(a); }, repeat);
        const double t_unroll = benchmark([&] { sink += sum_unroll4(a); }, repeat);
        const double t_pairwise = benchmark([&] { sink += sum_pairwise(a); }, repeat);
        (void)sink;

        print_table_row("sum_naive", n, repeat, t_naive, 1.0);
        print_table_row("sum_dual", n, repeat, t_dual, t_naive / t_dual);
        print_table_row("sum_unroll4", n, repeat, t_unroll, t_naive / t_unroll);
        print_table_row("sum_pairwise", n, repeat, t_pairwise, t_naive / t_pairwise);
    }
    return 0;
}
