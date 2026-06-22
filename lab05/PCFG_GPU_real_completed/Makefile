HIPCC ?= hipcc
CXXFLAGS ?= -O2 -std=c++17

BIN_DIR := bin
GPU_TEST := $(BIN_DIR)/pcfg_gpu_test
GPU_SRCS := src/gpu/pcfg_gpu_test.cpp src/gpu/pcfg_gpu_generate.hip
GPU_HDRS := src/gpu/pcfg_gpu_generate.h
REAL_PCFG_TEST := $(BIN_DIR)/pcfg_real_gpu_test
REAL_PCFG_SRCS := src/gpu/pcfg_real_end_to_end.cpp \
	               src/gpu/pcfg_gpu_generate.hip \
	               pcfg_gpu/guess_mpi_advanced/train.cpp \
	               pcfg_gpu/guess_mpi_advanced/guessing.cpp

.PHONY: gpu real-pcfg clean

gpu: $(GPU_TEST)

real-pcfg: $(REAL_PCFG_TEST)

$(GPU_TEST): $(GPU_SRCS) $(GPU_HDRS)
	mkdir -p $(BIN_DIR)
	$(HIPCC) $(CXXFLAGS) $(GPU_SRCS) -o $@

$(REAL_PCFG_TEST): $(REAL_PCFG_SRCS) $(GPU_HDRS) pcfg_gpu/guess_mpi_advanced/PCFG.h
	mkdir -p $(BIN_DIR)
	$(HIPCC) $(CXXFLAGS) -Isrc/gpu -Ipcfg_gpu/guess_mpi_advanced $(REAL_PCFG_SRCS) -o $@

clean:
	rm -f $(GPU_TEST) $(REAL_PCFG_TEST)
