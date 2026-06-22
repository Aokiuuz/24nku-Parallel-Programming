HIPCC ?= hipcc
CXXFLAGS ?= -O2 -std=c++17

BIN_DIR := bin
GPU_TEST := $(BIN_DIR)/pcfg_gpu_test
GPU_SRCS := src/gpu/pcfg_gpu_test.cpp src/gpu/pcfg_gpu_generate.hip
GPU_HDRS := src/gpu/pcfg_gpu_generate.h

.PHONY: gpu clean

gpu: $(GPU_TEST)

$(GPU_TEST): $(GPU_SRCS) $(GPU_HDRS)
	mkdir -p $(BIN_DIR)
	$(HIPCC) $(CXXFLAGS) $(GPU_SRCS) -o $@

clean:
	rm -f $(GPU_TEST)
