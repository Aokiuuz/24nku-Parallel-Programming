#include "PCFG.h"
#include <fstream>
#include <cctype>
#include <algorithm>
#include <cstdlib>
#include <limits>
#include <pthread.h>

namespace
{
const int kMaxTrainThreads = 8;

int ReadTrainThreadCount()
{
    const char *raw = getenv("PCFG_TRAIN_THREADS");
    if (raw == nullptr)
    {
        raw = getenv("PCFG_THREADS");
    }
    if (raw == nullptr)
    {
        raw = getenv("PTHREAD_NUM_THREADS");
    }

    if (raw == nullptr)
    {
        return 4;
    }

    int thread_count = atoi(raw);
    return thread_count > 0 ? thread_count : 4;
}

int GetTrainWorkerCount(size_t password_count)
{
    if (password_count == 0)
    {
        return 1;
    }

    int thread_count = ReadTrainThreadCount();
    if (thread_count > kMaxTrainThreads)
    {
        thread_count = kMaxTrainThreads;
    }
    if (thread_count > static_cast<int>(password_count))
    {
        thread_count = static_cast<int>(password_count);
    }
    return thread_count > 0 ? thread_count : 1;
}

struct SegmentKey
{
    int type;
    int length;

    bool operator==(const SegmentKey &other) const
    {
        return type == other.type && length == other.length;
    }
};

struct SegmentKeyHash
{
    size_t operator()(const SegmentKey &key) const
    {
        return static_cast<size_t>(key.type * 131 + key.length);
    }
};

struct SegmentStat
{
    int type = 0;
    int length = 0;
    int count = 0;
    unsigned long long first_order = numeric_limits<unsigned long long>::max();
    unordered_map<string, int> value_counts;
    unordered_map<string, unsigned long long> value_first_order;
};

struct PTStat
{
    vector<segment> content;
    int count = 0;
    unsigned long long first_order = numeric_limits<unsigned long long>::max();
};

struct TrainStats
{
    int total_preterm = 0;
    unordered_map<SegmentKey, SegmentStat, SegmentKeyHash> segments;
    unordered_map<string, PTStat> preterminals;
};

struct TrainTask
{
    const vector<string> *passwords;
    size_t begin;
    size_t end;
    TrainStats *stats;
};

unsigned long long MakeSegmentOrder(size_t line_index, size_t event_index)
{
    return (static_cast<unsigned long long>(line_index) << 20) + event_index;
}

string MakePTKey(const vector<segment> &content)
{
    string key;
    for (const segment &seg : content)
    {
        key += char('0' + seg.type);
        key += ':';
        key += to_string(seg.length);
        key += '|';
    }
    return key;
}

void RecordSegment(TrainStats &stats, const segment &seg, const string &value, unsigned long long order)
{
    SegmentKey key{seg.type, seg.length};
    SegmentStat &stat = stats.segments[key];
    stat.type = seg.type;
    stat.length = seg.length;
    stat.count += 1;
    if (order < stat.first_order)
    {
        stat.first_order = order;
    }

    stat.value_counts[value] += 1;
    auto value_order = stat.value_first_order.find(value);
    if (value_order == stat.value_first_order.end() || order < value_order->second)
    {
        stat.value_first_order[value] = order;
    }
}

void RecordPT(TrainStats &stats, const vector<segment> &content, size_t line_index)
{
    string key = MakePTKey(content);
    PTStat &stat = stats.preterminals[key];
    stat.count += 1;
    if (stat.content.empty())
    {
        stat.content = content;
    }
    if (line_index < stat.first_order)
    {
        stat.first_order = line_index;
    }
    stats.total_preterm += 1;
}

void ParsePasswordToStats(TrainStats &stats, const string &pw, size_t line_index)
{
    vector<segment> content;
    string curr_part;
    int curr_type = 0;
    size_t event_index = 0;

    auto flush_segment = [&]()
    {
        if (curr_part.empty())
        {
            return;
        }
        segment seg(curr_type, curr_part.length());
        RecordSegment(stats, seg, curr_part, MakeSegmentOrder(line_index, event_index));
        event_index += 1;
        content.emplace_back(seg);
        curr_part.clear();
    };

    for (char ch : pw)
    {
        int next_type = 3;
        if (isalpha(ch))
        {
            next_type = 1;
        }
        else if (isdigit(ch))
        {
            next_type = 2;
        }

        if (curr_type != 0 && curr_type != next_type)
        {
            flush_segment();
        }
        curr_type = next_type;
        curr_part += ch;
    }

    flush_segment();
    RecordPT(stats, content, line_index);
}

void *TrainWorker(void *arg)
{
    TrainTask *task = static_cast<TrainTask *>(arg);
    const vector<string> &passwords = *(task->passwords);
    TrainStats &stats = *(task->stats);

    for (size_t i = task->begin; i < task->end; i += 1)
    {
        ParsePasswordToStats(stats, passwords[i], i);
    }

    return nullptr;
}

void MergeStats(TrainStats &dst, const TrainStats &src)
{
    dst.total_preterm += src.total_preterm;

    for (const auto &entry : src.segments)
    {
        const SegmentKey &key = entry.first;
        const SegmentStat &src_stat = entry.second;
        SegmentStat &dst_stat = dst.segments[key];
        dst_stat.type = src_stat.type;
        dst_stat.length = src_stat.length;
        dst_stat.count += src_stat.count;
        if (src_stat.first_order < dst_stat.first_order)
        {
            dst_stat.first_order = src_stat.first_order;
        }

        for (const auto &value_entry : src_stat.value_counts)
        {
            const string &value = value_entry.first;
            dst_stat.value_counts[value] += value_entry.second;
            unsigned long long order = src_stat.value_first_order.at(value);
            auto dst_order = dst_stat.value_first_order.find(value);
            if (dst_order == dst_stat.value_first_order.end() || order < dst_order->second)
            {
                dst_stat.value_first_order[value] = order;
            }
        }
    }

    for (const auto &entry : src.preterminals)
    {
        const string &key = entry.first;
        const PTStat &src_stat = entry.second;
        PTStat &dst_stat = dst.preterminals[key];
        dst_stat.count += src_stat.count;
        if (dst_stat.content.empty())
        {
            dst_stat.content = src_stat.content;
        }
        if (src_stat.first_order < dst_stat.first_order)
        {
            dst_stat.first_order = src_stat.first_order;
        }
    }
}

void FillSegment(segment &dst, const SegmentStat &src)
{
    vector<pair<unsigned long long, string>> ordered_values;
    for (const auto &entry : src.value_counts)
    {
        ordered_values.emplace_back(src.value_first_order.at(entry.first), entry.first);
    }
    sort(ordered_values.begin(), ordered_values.end());

    for (const auto &entry : ordered_values)
    {
        int id = dst.values.size();
        const string &value = entry.second;
        dst.values[value] = id;
        dst.freqs[id] = src.value_counts.at(value);
    }
}

void BuildSegments(model &dst, const TrainStats &stats, int type)
{
    vector<const SegmentStat *> ordered_segments;
    for (const auto &entry : stats.segments)
    {
        if (entry.second.type == type)
        {
            ordered_segments.emplace_back(&entry.second);
        }
    }
    sort(ordered_segments.begin(), ordered_segments.end(),
         [](const SegmentStat *a, const SegmentStat *b)
         {
             return a->first_order < b->first_order;
         });

    for (const SegmentStat *src : ordered_segments)
    {
        segment dst_seg(src->type, src->length);
        FillSegment(dst_seg, *src);

        if (type == 1)
        {
            int id = dst.GetNextLettersID();
            dst.letters.emplace_back(dst_seg);
            dst.letters_freq[id] = src->count;
        }
        else if (type == 2)
        {
            int id = dst.GetNextDigitsID();
            dst.digits.emplace_back(dst_seg);
            dst.digits_freq[id] = src->count;
        }
        else
        {
            int id = dst.GetNextSymbolsID();
            dst.symbols.emplace_back(dst_seg);
            dst.symbols_freq[id] = src->count;
        }
    }
}

void BuildModelFromStats(model &dst, const TrainStats &stats)
{
    dst.total_preterm = stats.total_preterm;

    BuildSegments(dst, stats, 1);
    BuildSegments(dst, stats, 2);
    BuildSegments(dst, stats, 3);

    vector<const PTStat *> ordered_pts;
    for (const auto &entry : stats.preterminals)
    {
        ordered_pts.emplace_back(&entry.second);
    }
    sort(ordered_pts.begin(), ordered_pts.end(),
         [](const PTStat *a, const PTStat *b)
         {
             return a->first_order < b->first_order;
         });

    for (const PTStat *src : ordered_pts)
    {
        PT pt;
        pt.content = src->content;
        for (int i = 0; i < static_cast<int>(pt.content.size()); i += 1)
        {
            pt.curr_indices.emplace_back(0);
        }

        int id = dst.GetNextPretermID();
        dst.preterminals.emplace_back(pt);
        dst.preterm_freq[id] = src->count;
    }
}
}

// 这个文件里面的各函数你都不需要完全理解，甚至根本不需要看
// 从学术价值上讲，加速模型的训练过程是一个没什么价值的问题，因为我们一般假定统计学模型的训练成本较低
// 但是，假如你是一个投稿时顶着ddl做实验的倒霉研究生/实习生，提高训练速度就可以大幅节省你的时间了
// 所以如果你愿意，也可以尝试用多线程加速训练过程

/**
 * 怎么加速PCFG训练过程？据助教所知，没有公开文献提出过有效的加速方法（因为这么做基本无学术价值）
 * 
 * 但是统计学模型好就好在其数据是可加的。例如，假如我把数据集拆分成4个部分，并行训练4个不同的模型。
 * 然后我可以直接将四个模型的统计数据进行简单加和，就得到了和串行训练相同的模型了。
 * 
 * 说起来容易，做起来不一定容易，你可能会碰到一系列具体的工程问题。如果你决定加速训练过程，祝你好运！
 * 
 */

// 训练的wrapper，实际上就是读取训练集
void model::train(string path)
{
    string pw;
    ifstream train_set(path);
    int lines = 0;
    vector<string> passwords;
    passwords.reserve(3010000);

    cout<<"Training..."<<endl;
    cout<<"Training phase 1: reading passwords..."<<endl;
    while (train_set >> pw)
    {
        lines += 1;
        if (lines % 10000 == 0)
        {
            cout <<"Lines processed: "<< lines << endl;
            // 在这里更改读取的训练集口令上限
            if (lines > 3000000)
            {
                break;
            }
        }
        passwords.emplace_back(pw);
    }

    int thread_count = GetTrainWorkerCount(passwords.size());
    cout << "Training phase 1b: parsing passwords with " << thread_count << " thread(s)..." << endl;
    if (thread_count == 1)
    {
        for (const string &password : passwords)
        {
            parse(password);
        }
        return;
    }

    vector<TrainStats> local_stats(thread_count);
    vector<pthread_t> threads(thread_count);
    vector<TrainTask> tasks(thread_count);
    size_t block = (passwords.size() + thread_count - 1) / thread_count;

    for (int tid = 0; tid < thread_count; tid += 1)
    {
        size_t begin = tid * block;
        size_t end = begin + block;
        if (end > passwords.size())
        {
            end = passwords.size();
        }
        tasks[tid] = TrainTask{&passwords, begin, end, &local_stats[tid]};
        pthread_create(&threads[tid], nullptr, TrainWorker, &tasks[tid]);
    }

    for (int tid = 0; tid < thread_count; tid += 1)
    {
        pthread_join(threads[tid], nullptr);
    }

    cout << "Training phase 1c: merging local statistics..." << endl;
    TrainStats merged_stats;
    for (int tid = 0; tid < thread_count; tid += 1)
    {
        MergeStats(merged_stats, local_stats[tid]);
    }
    BuildModelFromStats(*this, merged_stats);
}

/// @brief 在模型中找到一个PT的统计数据
/// @param pt 需要查找的PT
/// @return 目标PT在模型中的对应下标
int model::FindPT(PT pt)
{
    for (int id = 0; id < preterminals.size(); id += 1)
    {
        if (preterminals[id].content.size() != pt.content.size())
        {
            continue;
        }
        else
        {
            bool equal_flag = true;
            for (int idx = 0; idx < preterminals[id].content.size(); idx += 1)
            {
                if (preterminals[id].content[idx].type != pt.content[idx].type || preterminals[id].content[idx].length != pt.content[idx].length)
                {
                    equal_flag = false;
                    break;
                }
            }
            if (equal_flag == true)
            {
                return id;
            }
        }
    }
    return -1;
}

/// @brief 在模型中找到一个letter segment的统计数据
/// @param seg 要找的letter segment
/// @return 目标letter segment的对应下标
int model::FindLetter(segment seg)
{
    for (int id = 0; id < letters.size(); id += 1)
    {
        if (letters[id].length == seg.length)
        {
            return id;
        }
    }
    return -1;
}

/// @brief 在模型中找到一个digit segment的统计数据
/// @param seg 要找的digit segment
/// @return 目标digit segment的对应下标
int model::FindDigit(segment seg)
{
    for (int id = 0; id < digits.size(); id += 1)
    {
        if (digits[id].length == seg.length)
        {
            return id;
        }
    }
    return -1;
}

int model::FindSymbol(segment seg)
{
    for (int id = 0; id < symbols.size(); id += 1)
    {
        if (symbols[id].length == seg.length)
        {
            return id;
        }
    }
    return -1;
}

void PT::insert(segment seg)
{
    content.emplace_back(seg);
}

void segment::insert(string value)
{
    if (values.find(value) == values.end())
    {
        values[value] = values.size();
        freqs[values[value]] = 1;
    }
    else
    {
        freqs[values[value]] += 1;
    }
}


void segment::order()
{
    for (pair<string, int> value : values)
    {
        ordered_values.emplace_back(value.first);
    }
    // cout << "value size:" << ordered_values.size() << endl;
    std::sort(ordered_values.begin(), ordered_values.end(),
              [this](const std::string &a, const std::string &b)
              {
                  return freqs.at(values[a]) > freqs.at(values[b]);
              });

    // 将排序后的频率存入 ordered_freqs 并计算 total_freq
    for (const std::string &val : ordered_values)
    {
        ordered_freqs.emplace_back(freqs.at(values[val]));
        total_freq += freqs.at(values[val]);
    }
    for (string val : ordered_values)
    {
        ordered_freqs.emplace_back(freqs.at(values[val]));
        total_freq += freqs.at(values[val]);
    }
}

void model::parse(string pw)
{
    PT pt;
    string curr_part = "";
    int curr_type = 0; // 0: 未设置, 1: 字母, 2: 数字, 3: 特殊字符
    // 请学会使用这种方式写for循环：for (auto it : iterable)
    // 相信我，以后你会用上的。You're welcome :)
    for (char ch : pw)
    {
        if (isalpha(ch))
        {
            if (curr_type != 1)
            {
                if (curr_type == 2)
                {
                    segment seg(curr_type, curr_part.length());
                    if (FindDigit(seg) == -1)
                    {
                        int id = GetNextDigitsID();
                        digits.emplace_back(seg);
                        digits[id].insert(curr_part);
                        digits_freq[id] = 1;
                    }
                    else
                    {
                        int id = FindDigit(seg);
                        digits_freq[id] += 1;
                        digits[id].insert(curr_part);
                    }
                    curr_part.clear();
                    pt.insert(seg);
                }
                else if (curr_type == 3)
                {
                    segment seg(curr_type, curr_part.length());
                    if (FindSymbol(seg) == -1)
                    {
                        int id = GetNextSymbolsID();
                        symbols.emplace_back(seg);
                        symbols_freq[id] = 1;
                        symbols[id].insert(curr_part);
                    }
                    else
                    {
                        int id = FindSymbol(seg);
                        symbols_freq[id] += 1;
                        symbols[id].insert(curr_part);
                    }
                    curr_part.clear();
                    pt.insert(seg);
                }
            }
            curr_type = 1;
            curr_part += ch;
        }
        else if (isdigit(ch))
        {
            if (curr_type != 2)
            {
                if (curr_type == 1)
                {
                    segment seg(curr_type, curr_part.length());
                    if (FindLetter(seg) == -1)
                    {
                        int id = GetNextLettersID();
                        letters.emplace_back(seg);
                        letters_freq[id] = 1;
                        letters[id].insert(curr_part);
                    }
                    else
                    {
                        int id = FindLetter(seg);
                        letters_freq[id] += 1;
                        letters[id].insert(curr_part);
                    }
                    curr_part.clear();
                    pt.insert(seg);
                }
                else if (curr_type == 3)
                {
                    segment seg(curr_type, curr_part.length());
                    if (FindSymbol(seg) == -1)
                    {
                        int id = GetNextSymbolsID();
                        symbols.emplace_back(seg);
                        symbols_freq[id] = 1;
                        symbols[id].insert(curr_part);
                    }
                    else
                    {
                        int id = FindSymbol(seg);
                        symbols_freq[id] += 1;
                        symbols[id].insert(curr_part);
                    }
                    curr_part.clear();
                    pt.insert(seg);
                }
            }
            curr_type = 2;
            curr_part += ch;
        }
        else
        {
            if (curr_type != 3)
            {
                if (curr_type == 1)
                {
                    segment seg(curr_type, curr_part.length());
                    if (FindLetter(seg) == -1)
                    {
                        int id = GetNextLettersID();
                        letters.emplace_back(seg);
                        letters_freq[id] = 1;
                        letters[id].insert(curr_part);
                    }
                    else
                    {
                        int id = FindLetter(seg);
                        letters_freq[id] += 1;
                        letters[id].insert(curr_part);
                    }
                    curr_part.clear();
                    pt.insert(seg);
                }
                else if (curr_type == 2)
                {
                    segment seg(curr_type, curr_part.length());
                    if (FindDigit(seg) == -1)
                    {
                        int id = GetNextDigitsID();
                        digits.emplace_back(seg);
                        digits_freq[id] = 1;
                        digits[id].insert(curr_part);
                    }
                    else
                    {
                        int id = FindDigit(seg);
                        digits_freq[id] += 1;
                        digits[id].insert(curr_part);
                    }
                    curr_part.clear();
                    pt.insert(seg);
                }
            }
            curr_type = 3;
            curr_part += ch;
        }
    }
    if (!curr_part.empty())
    {
        if (curr_type == 1)
        {
            segment seg(curr_type, curr_part.length());
            if (FindLetter(seg) == -1)
            {
                int id = GetNextLettersID();
                letters.emplace_back(seg);
                letters_freq[id] = 1;
                letters[id].insert(curr_part);
            }
            else
            {
                int id = FindLetter(seg);
                letters_freq[id] += 1;
                letters[id].insert(curr_part);
            }
            curr_part.clear();
            pt.insert(seg);
        }
        else if (curr_type == 2)
        {
            segment seg(curr_type, curr_part.length());
            if (FindDigit(seg) == -1)
            {
                int id = GetNextDigitsID();
                digits.emplace_back(seg);
                digits_freq[id] = 1;
                digits[id].insert(curr_part);
            }
            else
            {
                int id = FindDigit(seg);
                digits_freq[id] += 1;
                digits[id].insert(curr_part);
            }
            curr_part.clear();
            pt.insert(seg);
        }
        else
        {
            segment seg(curr_type, curr_part.length());
            if (FindSymbol(seg) == -1)
            {
                int id = GetNextSymbolsID();
                symbols.emplace_back(seg);
                symbols_freq[id] = 1;
                symbols[id].insert(curr_part);
            }
            else
            {
                int id = FindSymbol(seg);
                symbols_freq[id] += 1;
                symbols[id].insert(curr_part);
            }
            curr_part.clear();
            pt.insert(seg);
        }
    }
    // pt.PrintPT();
    // cout<<endl;
    // cout << FindPT(pt) << endl;
    total_preterm += 1;
    if (FindPT(pt) == -1)
    {
        for (int i = 0; i < pt.content.size(); i += 1)
        {
            pt.curr_indices.emplace_back(0);
        }
        int id = GetNextPretermID();
        // cout << id << endl;
        preterminals.emplace_back(pt);
        preterm_freq[id] = 1;
    }
    else
    {
        int id = FindPT(pt);
        // cout << id << endl;
        preterm_freq[id] += 1;
    }
}

void segment::PrintSeg()
{
    if (type == 1)
    {
        cout << "L" << length;
    }
    if (type == 2)
    {
        cout << "D" << length;
    }
    if (type == 3)
    {
        cout << "S" << length;
    }
}

void segment::PrintValues()
{
    // order();
    for (string iter : ordered_values)
    {
        cout << iter << " freq:" << freqs[values[iter]] << endl;
    }
}

void PT::PrintPT()
{
    for (auto iter : content)
    {
        iter.PrintSeg();
    }
}

void model::print()
{
    cout << "preterminals:" << endl;
    for (int i = 0; i < preterminals.size(); i += 1)
    {
        preterminals[i].PrintPT();
        // cout << preterminals[i].curr_indices.size() << endl;
        cout << " freq:" << preterm_freq[i];
        cout << endl;
    }
    // order();
    for (auto iter : ordered_pts)
    {
        iter.PrintPT();
        cout << " freq:" << preterm_freq[FindPT(iter)];
        cout << endl;
    }
    cout << "segments:" << endl;
    for (int i = 0; i < letters.size(); i += 1)
    {
        letters[i].PrintSeg();
        // letters[i].PrintValues();
        cout << " freq:" << letters_freq[i];
        cout << endl;
    }
    for (int i = 0; i < digits.size(); i += 1)
    {
        digits[i].PrintSeg();
        // digits[i].PrintValues();
        cout << " freq:" << digits_freq[i];
        cout << endl;
    }
    for (int i = 0; i < symbols.size(); i += 1)
    {
        symbols[i].PrintSeg();
        // symbols[i].PrintValues();
        cout << " freq:" << symbols_freq[i];
        cout << endl;
    }
}

bool compareByPretermProb(const PT& a, const PT& b) {
    return a.preterm_prob > b.preterm_prob;  // 降序排序
}

void model::order()
{
    cout << "Training phase 2: Ordering segment values and PTs..." << endl;
    for (PT pt : preterminals)
    {
        pt.preterm_prob = float(preterm_freq[FindPT(pt)]) / total_preterm;
        ordered_pts.emplace_back(pt);
    }
    bool swapped;
    cout << "total pts" << ordered_pts.size() << endl;
    std::sort(ordered_pts.begin(), ordered_pts.end(), compareByPretermProb);
    cout << "Ordering letters" << endl;
    // cout << "total letters" << endl;
    for (int i = 0; i < letters.size(); i += 1)
    {
        // cout << i << endl;
        letters[i].order();
    }
    cout << "Ordering digits" << endl;
    // cout << "total letters" << endl;
    for (int i = 0; i < digits.size(); i += 1)
    {
        digits[i].order();
    }
    cout << "ordering symbols" << endl;
    // cout << "total letters" << endl;
    for (int i = 0; i < symbols.size(); i += 1)
    {
        symbols[i].order();
    }
}
