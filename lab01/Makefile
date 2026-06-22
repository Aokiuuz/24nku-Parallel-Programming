CXX ?= g++
CXXFLAGS ?= -std=c++17 -Wall -Wextra

SRC_DIR := src
BIN_DIR := bin
MKDIR_P := powershell -Command "New-Item -ItemType Directory -Force '$(BIN_DIR)' | Out-Null"
RM_RF := powershell -Command "Remove-Item -Recurse -Force -ErrorAction SilentlyContinue '$(BIN_DIR)'"

TARGETS := $(BIN_DIR)/matrix_dot $(BIN_DIR)/sum_bench

.PHONY: all clean o0 o2 o3 vtune vtune_o0 vtune_o2

all: o2

$(BIN_DIR):
	$(MKDIR_P)

$(BIN_DIR)/matrix_dot: $(SRC_DIR)/matrix_dot.cpp $(SRC_DIR)/common.hpp | $(BIN_DIR)
	$(CXX) $(CXXFLAGS) -O2 $< -o $@

$(BIN_DIR)/sum_bench: $(SRC_DIR)/sum_bench.cpp $(SRC_DIR)/common.hpp | $(BIN_DIR)
	$(CXX) $(CXXFLAGS) -O2 $< -o $@

o0: CXXFLAGS += -O0
o0: $(BIN_DIR)
	$(CXX) $(CXXFLAGS) $(SRC_DIR)/matrix_dot.cpp -o $(BIN_DIR)/matrix_dot_o0
	$(CXX) $(CXXFLAGS) $(SRC_DIR)/sum_bench.cpp -o $(BIN_DIR)/sum_bench_o0

o2: CXXFLAGS += -O2
o2: $(BIN_DIR)
	$(CXX) $(CXXFLAGS) $(SRC_DIR)/matrix_dot.cpp -o $(BIN_DIR)/matrix_dot_o2
	$(CXX) $(CXXFLAGS) $(SRC_DIR)/sum_bench.cpp -o $(BIN_DIR)/sum_bench_o2

o3: CXXFLAGS += -O3
o3: $(BIN_DIR)
	$(CXX) $(CXXFLAGS) $(SRC_DIR)/matrix_dot.cpp -o $(BIN_DIR)/matrix_dot_o3
	$(CXX) $(CXXFLAGS) $(SRC_DIR)/sum_bench.cpp -o $(BIN_DIR)/sum_bench_o3

vtune_o0: CXXFLAGS += -O0 -g
vtune_o0: $(BIN_DIR)
	$(CXX) $(CXXFLAGS) $(SRC_DIR)/matrix_dot.cpp -o $(BIN_DIR)/matrix_dot_o0_vtune
	$(CXX) $(CXXFLAGS) $(SRC_DIR)/sum_bench.cpp -o $(BIN_DIR)/sum_bench_o0_vtune

vtune_o2: CXXFLAGS += -O2 -g
vtune_o2: $(BIN_DIR)
	$(CXX) $(CXXFLAGS) $(SRC_DIR)/matrix_dot.cpp -o $(BIN_DIR)/matrix_dot_o2_vtune
	$(CXX) $(CXXFLAGS) $(SRC_DIR)/sum_bench.cpp -o $(BIN_DIR)/sum_bench_o2_vtune

vtune: CXXFLAGS += -O3 -g
vtune: $(BIN_DIR)
	$(CXX) $(CXXFLAGS) $(SRC_DIR)/matrix_dot.cpp -o $(BIN_DIR)/matrix_dot_vtune
	$(CXX) $(CXXFLAGS) $(SRC_DIR)/sum_bench.cpp -o $(BIN_DIR)/sum_bench_vtune

clean:
	$(RM_RF)
