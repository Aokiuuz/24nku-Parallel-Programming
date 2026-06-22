#include "PCFG.h"
#include <chrono>
#include <cstdlib>
#include <pthread.h>
using namespace std;
using namespace chrono;

namespace
{
const int kPthreadMinWorkPerThread = 256;

double SecondsSince(steady_clock::time_point begin, steady_clock::time_point end)
{
    return duration_cast<duration<double>>(end - begin).count();
}

struct GenerateTask
{
    int begin;
    int end;
    size_t base;
    const string *prefix;
    const vector<string> *values;
    vector<string> *output;
};

int ReadThreadCountFromEnv()
{
    const char *raw = getenv("PCFG_THREADS");
    if (raw == nullptr)
    {
        raw = getenv("PTHREAD_NUM_THREADS");
    }
    if (raw == nullptr)
    {
        raw = getenv("THREAD_NUM");
    }

    if (raw == nullptr)
    {
        return 4;
    }

    int thread_count = atoi(raw);
    return thread_count > 0 ? thread_count : 4;
}

int GetWorkerCount(int value_count)
{
    if (value_count <= 0)
    {
        return 1;
    }

    int thread_count = ReadThreadCountFromEnv();
    if (thread_count > 8)
    {
        thread_count = 8;
    }
    if (thread_count > value_count)
    {
        thread_count = value_count;
    }
    return thread_count > 0 ? thread_count : 1;
}

void *GenerateWorker(void *arg)
{
    GenerateTask *task = static_cast<GenerateTask *>(arg);
    const string &prefix = *(task->prefix);
    const vector<string> &values = *(task->values);
    vector<string> &output = *(task->output);

    if (prefix.empty())
    {
        for (int i = task->begin; i < task->end; i += 1)
        {
            output[task->base + i] = values[i];
        }
    }
    else
    {
        for (int i = task->begin; i < task->end; i += 1)
        {
            output[task->base + i] = prefix + values[i];
        }
    }

    return nullptr;
}

void AppendSegmentValuesPthread(vector<string> &output, const string &prefix, const vector<string> &values, int value_count)
{
    const size_t base = output.size();
    output.resize(base + value_count);

    int thread_count = GetWorkerCount(value_count);
    if (thread_count == 1 || value_count < kPthreadMinWorkPerThread)
    {
        GenerateTask task{0, value_count, base, &prefix, &values, &output};
        GenerateWorker(&task);
        return;
    }

    vector<pthread_t> threads(thread_count);
    vector<GenerateTask> tasks(thread_count);
    int block = (value_count + thread_count - 1) / thread_count;

    for (int tid = 0; tid < thread_count; tid += 1)
    {
        int begin = tid * block;
        int end = begin + block;
        if (end > value_count)
        {
            end = value_count;
        }

        tasks[tid] = GenerateTask{begin, end, base, &prefix, &values, &output};
        pthread_create(&threads[tid], nullptr, GenerateWorker, &tasks[tid]);
    }

    for (int tid = 0; tid < thread_count; tid += 1)
    {
        pthread_join(threads[tid], nullptr);
    }
}
}

void PriorityQueue::CalProb(PT &pt)
{
    // 计算PriorityQueue里面一个PT的流程如下：
    // 1. 首先需要计算一个PT本身的概率。例如，L6S1的概率为0.15
    // 2. 需要注意的是，Queue里面的PT不是“纯粹的”PT，而是除了最后一个segment以外，全部被value实例化的PT
    // 3. 所以，对于L6S1而言，其在Queue里面的实际PT可能是123456S1，其中“123456”为L6的一个具体value。
    // 4. 这个时候就需要计算123456在L6中出现的概率了。假设123456在所有L6 segment中的概率为0.1，那么123456S1的概率就是0.1*0.15

    // 计算一个PT本身的概率。后续所有具体segment value的概率，直接累乘在这个初始概率值上
    pt.prob = pt.preterm_prob;

    // index: 标注当前segment在PT中的位置
    int index = 0;


    for (int idx : pt.curr_indices)
    {
        // pt.content[index].PrintSeg();
        if (pt.content[index].type == 1)
        {
            // 下面这行代码的意义：
            // pt.content[index]：目前需要计算概率的segment
            // m.FindLetter(seg): 找到一个letter segment在模型中的对应下标
            // m.letters[m.FindLetter(seg)]：一个letter segment在模型中对应的所有统计数据
            // m.letters[m.FindLetter(seg)].ordered_values：一个letter segment在模型中，所有value的总数目
            pt.prob *= m.letters[m.FindLetter(pt.content[index])].ordered_freqs[idx];
            pt.prob /= m.letters[m.FindLetter(pt.content[index])].total_freq;
            // cout << m.letters[m.FindLetter(pt.content[index])].ordered_freqs[idx] << endl;
            // cout << m.letters[m.FindLetter(pt.content[index])].total_freq << endl;
        }
        if (pt.content[index].type == 2)
        {
            pt.prob *= m.digits[m.FindDigit(pt.content[index])].ordered_freqs[idx];
            pt.prob /= m.digits[m.FindDigit(pt.content[index])].total_freq;
            // cout << m.digits[m.FindDigit(pt.content[index])].ordered_freqs[idx] << endl;
            // cout << m.digits[m.FindDigit(pt.content[index])].total_freq << endl;
        }
        if (pt.content[index].type == 3)
        {
            pt.prob *= m.symbols[m.FindSymbol(pt.content[index])].ordered_freqs[idx];
            pt.prob /= m.symbols[m.FindSymbol(pt.content[index])].total_freq;
            // cout << m.symbols[m.FindSymbol(pt.content[index])].ordered_freqs[idx] << endl;
            // cout << m.symbols[m.FindSymbol(pt.content[index])].total_freq << endl;
        }
        index += 1;
    }
    // cout << pt.prob << endl;
}

void PriorityQueue::init()
{
    // cout << m.ordered_pts.size() << endl;
    // 用所有可能的PT，按概率降序填满整个优先队列
    for (PT pt : m.ordered_pts)
    {
        for (segment seg : pt.content)
        {
            if (seg.type == 1)
            {
                // 下面这行代码的意义：
                // max_indices用来表示PT中各个segment的可能数目。例如，L6S1中，假设模型统计到了100个L6，那么L6对应的最大下标就是99
                // （但由于后面采用了"<"的比较关系，所以其实max_indices[0]=100）
                // m.FindLetter(seg): 找到一个letter segment在模型中的对应下标
                // m.letters[m.FindLetter(seg)]：一个letter segment在模型中对应的所有统计数据
                // m.letters[m.FindLetter(seg)].ordered_values：一个letter segment在模型中，所有value的总数目
                pt.max_indices.emplace_back(m.letters[m.FindLetter(seg)].ordered_values.size());
            }
            if (seg.type == 2)
            {
                pt.max_indices.emplace_back(m.digits[m.FindDigit(seg)].ordered_values.size());
            }
            if (seg.type == 3)
            {
                pt.max_indices.emplace_back(m.symbols[m.FindSymbol(seg)].ordered_values.size());
            }
        }
        pt.preterm_prob = float(m.preterm_freq[m.FindPT(pt)]) / m.total_preterm;
        // pt.PrintPT();
        // cout << " " << m.preterm_freq[m.FindPT(pt)] << " " << m.total_preterm << " " << pt.preterm_prob << endl;

        // 计算当前pt的概率
        CalProb(pt);
        priority.emplace_back(pt);
    }
    // cout << "priority size:" << priority.size() << endl;
}

bool PriorityQueue::Empty() const
{
    return priority_head >= priority.size();
}

void PriorityQueue::PopNext()
{
    auto pop_begin = steady_clock::now();
    PT current = priority[priority_head];

    // 对优先队列最前面的PT，首先利用这个PT生成一系列猜测
    auto generate_begin = steady_clock::now();
    Generate(current);
    auto generate_end = steady_clock::now();
    profile_generate_time += SecondsSince(generate_begin, generate_end);

    // 然后需要根据即将出队的PT，生成一系列新的PT
    auto newpt_begin = steady_clock::now();
    vector<PT> new_pts = current.NewPTs();
    auto newpt_end = steady_clock::now();
    profile_newpt_time += SecondsSince(newpt_begin, newpt_end);
    profile_newpt_count += new_pts.size();

    for (PT pt : new_pts)
    {
        // 计算概率
        auto calprob_begin = steady_clock::now();
        CalProb(pt);
        auto calprob_end = steady_clock::now();
        profile_calprob_time += SecondsSince(calprob_begin, calprob_end);

        // 保持原始版本的线性扫描插入规则，只跳过已经逻辑出队的前缀。
        auto insert_begin = steady_clock::now();
        auto begin = priority.begin() + priority_head;
        for (auto iter = begin; iter != priority.end(); iter++)
        {
            if (iter != priority.end() - 1 && iter != begin)
            {
                if (pt.prob <= iter->prob && pt.prob > (iter + 1)->prob)
                {
                    priority.emplace(iter + 1, pt);
                    break;
                }
            }
            if (iter == priority.end() - 1)
            {
                priority.emplace_back(pt);
                break;
            }
            if (iter == begin && iter->prob < pt.prob)
            {
                priority.emplace(iter, pt);
                break;
            }
        }
        profile_queue_push_count += 1;
        auto insert_end = steady_clock::now();
        profile_queue_push_time += SecondsSince(insert_begin, insert_end);
    }

    auto erase_begin = steady_clock::now();
    priority_head += 1;
    auto erase_end = steady_clock::now();
    profile_queue_pop_time += SecondsSince(erase_begin, erase_end);

    auto pop_end = steady_clock::now();
    profile_popnext_time += SecondsSince(pop_begin, pop_end);
    profile_popnext_count += 1;
}

// 这个函数你就算看不懂，对并行算法的实现影响也不大
// 当然如果你想做一个基于多优先队列的并行算法，可能得稍微看一看了
vector<PT> PT::NewPTs()
{
    // 存储生成的新PT
    vector<PT> res;

    // 假如这个PT只有一个segment
    // 那么这个segment的所有value在出队前就已经被遍历完毕，并作为猜测输出
    // 因此，所有这个PT可能对应的口令猜测已经遍历完成，无需生成新的PT
    if (content.size() == 1)
    {
        return res;
    }
    else
    {
        // 最初的pivot值。我们将更改位置下标大于等于这个pivot值的segment的值（最后一个segment除外），并且一次只更改一个segment
        // 上面这句话里是不是有没看懂的地方？接着往下看你应该会更明白
        int init_pivot = pivot;

        // 开始遍历所有位置值大于等于init_pivot值的segment
        // 注意i < curr_indices.size() - 1，也就是除去了最后一个segment（这个segment的赋值预留给并行环节）
        for (int i = pivot; i < curr_indices.size() - 1; i += 1)
        {
            // curr_indices: 标记各segment目前的value在模型里对应的下标
            curr_indices[i] += 1;

            // max_indices：标记各segment在模型中一共有多少个value
            if (curr_indices[i] < max_indices[i])
            {
                // 更新pivot值
                pivot = i;
                res.emplace_back(*this);
            }

            // 这个步骤对于你理解pivot的作用、新PT生成的过程而言，至关重要
            curr_indices[i] -= 1;
        }
        pivot = init_pivot;
        return res;
    }

    return res;
}


// 这个函数是PCFG并行化算法的主要载体
// 尽量看懂，然后进行并行实现
void PriorityQueue::Generate(PT pt)
{
    // 计算PT的概率，这里主要是给PT的概率进行初始化
    CalProb(pt);

    // 对于只有一个segment的PT，直接遍历生成其中的所有value即可
    if (pt.content.size() == 1)
    {
        // 指向最后一个segment的指针，这个指针实际指向模型中的统计数据
        segment *a;
        // 在模型中定位到这个segment
        if (pt.content[0].type == 1)
        {
            a = &m.letters[m.FindLetter(pt.content[0])];
        }
        if (pt.content[0].type == 2)
        {
            a = &m.digits[m.FindDigit(pt.content[0])];
        }
        if (pt.content[0].type == 3)
        {
            a = &m.symbols[m.FindSymbol(pt.content[0])];
        }
        
        int value_count = pt.max_indices[0];
        const string empty_prefix;
        AppendSegmentValuesPthread(guesses, empty_prefix, a->ordered_values, value_count);
        total_guesses += value_count;
    }
    else
    {
        string guess;
        int seg_idx = 0;
        // 这个for循环的作用：给当前PT的所有segment赋予实际的值（最后一个segment除外）
        // segment值根据curr_indices中对应的值加以确定
        // 这个for循环你看不懂也没太大问题，并行算法不涉及这里的加速
        for (int idx : pt.curr_indices)
        {
            if (pt.content[seg_idx].type == 1)
            {
                guess += m.letters[m.FindLetter(pt.content[seg_idx])].ordered_values[idx];
            }
            if (pt.content[seg_idx].type == 2)
            {
                guess += m.digits[m.FindDigit(pt.content[seg_idx])].ordered_values[idx];
            }
            if (pt.content[seg_idx].type == 3)
            {
                guess += m.symbols[m.FindSymbol(pt.content[seg_idx])].ordered_values[idx];
            }
            seg_idx += 1;
            if (seg_idx == pt.content.size() - 1)
            {
                break;
            }
        }

        // 指向最后一个segment的指针，这个指针实际指向模型中的统计数据
        segment *a;
        if (pt.content[pt.content.size() - 1].type == 1)
        {
            a = &m.letters[m.FindLetter(pt.content[pt.content.size() - 1])];
        }
        if (pt.content[pt.content.size() - 1].type == 2)
        {
            a = &m.digits[m.FindDigit(pt.content[pt.content.size() - 1])];
        }
        if (pt.content[pt.content.size() - 1].type == 3)
        {
            a = &m.symbols[m.FindSymbol(pt.content[pt.content.size() - 1])];
        }
        
        int value_count = pt.max_indices[pt.content.size() - 1];
        AppendSegmentValuesPthread(guesses, guess, a->ordered_values, value_count);
        total_guesses += value_count;
    }
}
