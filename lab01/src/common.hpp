#pragma once

#include <chrono>
#include <cmath>
#include <cstddef>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <string>
#include <vector>

inline double now_seconds() {
    using clock = std::chrono::high_resolution_clock;
    const auto tp = clock::now().time_since_epoch();
    return std::chrono::duration<double>(tp).count();
}

template <class Func>
double benchmark(Func&& func, int repeat) {
    const double start = now_seconds();
    for (int i = 0; i < repeat; ++i) {
        func();
    }
    const double end = now_seconds();
    return end - start;
}

inline bool almost_equal(double lhs, double rhs, double eps = 1e-9) {
    return std::abs(lhs - rhs) <= eps * std::max(1.0, std::max(std::abs(lhs), std::abs(rhs)));
}

inline void print_table_header(const std::string& title) {
    std::cout << "\n=== " << title << " ===\n";
    std::cout << std::left << std::setw(20) << "algorithm"
              << std::setw(12) << "size"
              << std::setw(12) << "repeat"
              << std::setw(16) << "seconds"
              << std::setw(16) << "speedup"
              << '\n';
}

inline void print_table_row(
    const std::string& name,
    std::size_t size,
    int repeat,
    double seconds,
    double speedup
) {
    std::cout << std::left << std::setw(20) << name
              << std::setw(12) << size
              << std::setw(12) << repeat
              << std::setw(16) << std::fixed << std::setprecision(6) << seconds
              << std::setw(16) << std::fixed << std::setprecision(3) << speedup
              << '\n';
}
