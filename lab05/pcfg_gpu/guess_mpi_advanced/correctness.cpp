#include "md5.h"
#include <iomanip>
#include <sstream>
#include <string>
#include <vector>
using namespace std;

static string Md5StateToHex(const bit32 state[4])
{
    stringstream ss;
    for (int i = 0; i < 4; i += 1)
    {
        ss << setw(8) << setfill('0') << hex << state[i];
    }
    return ss.str();
}

static string SimdLaneToHex(uint32x4_t state[4], int lane)
{
    uint32_t lanes[4][4];
    for (int word = 0; word < 4; word += 1)
    {
        vst1q_u32(lanes[word], state[word]);
    }

    stringstream ss;
    for (int word = 0; word < 4; word += 1)
    {
        ss << setw(8) << setfill('0') << hex << lanes[word][lane];
    }
    return ss.str();
}

static bool RunCorrectnessTests()
{
    vector<string> test_pws = {
        "123456", "password", "12345678", "qwerty",
        "123456789", "12345", "1234", "111111"
    };
    vector<string> test_hashes = {
        "e10adc3949ba59abbe56e057f20f883e",
        "5f4dcc3b5aa765d61d8327deb882cf99",
        "25d55ad283aa400af464c76d713c07ad",
        "d8578edf8458ce06fbc5bb76a58c5ca4",
        "25f9e794323b453885f5181f1b624d0b",
        "827ccb0eea8a706c4c34a16891f84e7b",
        "81dc9bdb52d04dc20036dbd8313ed055",
        "96e79218965eb72c92a549dd5a330112"
    };

    cout << "Testing MD5Hash correctness..." << endl;
    for (size_t i = 0; i < test_pws.size(); i += 1)
    {
        bit32 state[4];
        MD5Hash(test_pws[i], state);
        string got = Md5StateToHex(state);
        if (got != test_hashes[i])
        {
            cout << "MD5Hash test failed for " << test_pws[i] << "!" << endl;
            cout << "Expected: " << test_hashes[i] << "\nGot:      " << got << endl;
            return false;
        }
    }
    cout << "MD5Hash test passed!" << endl; //请不要修改这一行

    cout << "Testing MD5Hash_simdversion correctness..." << endl;
    for (size_t batch = 0; batch < test_pws.size(); batch += 4)
    {
        uint32x4_t simd_state[4];
        MD5Hash_simdversion(&test_pws[batch], simd_state);

        for (int lane = 0; lane < 4; lane += 1)
        {
            size_t idx = batch + lane;
            string got = SimdLaneToHex(simd_state, lane);
            if (got != test_hashes[idx])
            {
                cout << "MD5Hash SIMD test failed for " << test_pws[idx] << "!" << endl;
                cout << "Expected: " << test_hashes[idx] << "\nGot:      " << got << endl;
                return false;
            }
        }
    }
    cout << "MD5Hash_simdversion test passed!" << endl;

    return true;
}
