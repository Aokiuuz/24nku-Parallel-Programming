from pathlib import Path
from html import escape


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "svg_slides"
OUT.mkdir(exist_ok=True)


def t(x, y, text, cls="body", anchor="start"):
    return f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}">{escape(text)}</text>'


def lines(x, y, items, cls="body", gap=28, bullet=True):
    out = []
    for i, item in enumerate(items):
        yy = y + i * gap
        if bullet:
            out.append(f'<circle cx="{x}" cy="{yy - 5}" r="4.5" class="dot"/>')
            out.append(t(x + 18, yy, item, cls))
        else:
            out.append(t(x, yy, item, cls))
    return "\n".join(out)


def card(x, y, w, h, accent=None, cls="card"):
    stripe = ""
    if accent:
        stripe = f'<rect x="{x}" y="{y}" width="6" height="{h}" rx="3" fill="{accent}" opacity="0.9"/>'
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="22" class="{cls}"/>{stripe}'


def pill(x, y, w, text, fill, color="#FFFFFF"):
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="30" rx="15" fill="{fill}" opacity="0.96"/>'
        f'<text x="{x + w / 2}" y="{y + 20}" text-anchor="middle" fill="{color}" font-size="13" '
        f'font-weight="800">{escape(text)}</text>'
    )


def svg_page(body, title, slide_no, total=14):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720" role="img" aria-label="{escape(title)}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0B1020"/>
      <stop offset="56%" stop-color="#111827"/>
      <stop offset="100%" stop-color="#172033"/>
    </linearGradient>
    <linearGradient id="paper" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#F8FAFC"/>
      <stop offset="100%" stop-color="#E2E8F0"/>
    </linearGradient>
    <linearGradient id="blue" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#60A5FA"/>
      <stop offset="100%" stop-color="#2563EB"/>
    </linearGradient>
    <linearGradient id="green" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#34D399"/>
      <stop offset="100%" stop-color="#059669"/>
    </linearGradient>
    <linearGradient id="red" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#F87171"/>
      <stop offset="100%" stop-color="#DC2626"/>
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="16" stdDeviation="18" flood-color="#020617" flood-opacity="0.34"/>
    </filter>
    <style>
      .page {{ font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif; }}
      .card {{ fill: rgba(255,255,255,0.078); stroke: rgba(255,255,255,0.15); stroke-width: 1.1; }}
      .card2 {{ fill: rgba(255,255,255,0.112); stroke: rgba(255,255,255,0.20); stroke-width: 1.1; }}
      .lightcard {{ fill: rgba(248,250,252,0.95); stroke: rgba(15,23,42,0.08); stroke-width: 1.0; }}
      .kicker {{ fill: #93C5FD; font-size: 12.5px; font-weight: 800; letter-spacing: 1.8px; }}
      .title {{ fill: #F8FAFC; font-size: 36px; font-weight: 850; letter-spacing: 0; }}
      .h1 {{ fill: #F8FAFC; font-size: 52px; font-weight: 850; letter-spacing: 0; }}
      .h2 {{ fill: #F8FAFC; font-size: 22px; font-weight: 820; letter-spacing: 0; }}
      .h3 {{ fill: #E5E7EB; font-size: 18px; font-weight: 780; letter-spacing: 0; }}
      .body {{ fill: #CBD5E1; font-size: 16px; font-weight: 520; letter-spacing: 0; }}
      .body2 {{ fill: #E2E8F0; font-size: 18px; font-weight: 600; letter-spacing: 0; }}
      .small {{ fill: #94A3B8; font-size: 12.5px; font-weight: 520; letter-spacing: 0; }}
      .dark {{ fill: #111827; font-size: 16px; font-weight: 620; letter-spacing: 0; }}
      .darksmall {{ fill: #475569; font-size: 12.5px; font-weight: 560; letter-spacing: 0; }}
      .metric {{ fill: #F8FAFC; font-size: 44px; font-weight: 850; letter-spacing: 0; }}
      .metric2 {{ fill: #111827; font-size: 40px; font-weight: 850; letter-spacing: 0; }}
      .axis {{ stroke: rgba(255,255,255,0.20); stroke-width: 1; }}
      .line {{ fill: none; stroke-width: 4; stroke-linecap: round; stroke-linejoin: round; }}
      .thin {{ fill: none; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }}
      .dot {{ fill: #60A5FA; }}
      .node {{ fill: rgba(15,23,42,0.74); stroke: rgba(255,255,255,0.18); stroke-width: 1.1; }}
      .chip {{ fill: rgba(255,255,255,0.10); stroke: rgba(255,255,255,0.16); stroke-width: 1; }}
    </style>
  </defs>
  <rect class="page" width="1280" height="720" fill="url(#bg)"/>
  <circle cx="1128" cy="-86" r="280" fill="#2563EB" opacity="0.12"/>
  <circle cx="-70" cy="652" r="300" fill="#059669" opacity="0.10"/>
  <g class="page" filter="url(#shadow)">
{body}
  </g>
  <text x="48" y="692" class="small">Coroutine Technology Research · SVG Final Slides</text>
  <text x="1232" y="692" text-anchor="end" class="small">{slide_no:02d}/{total:02d}</text>
</svg>
'''


def slide_header(kicker, title, subtitle=None):
    sub = t(50, 128, subtitle, "body") if subtitle else ""
    return "\n".join([
        t(50, 52, kicker, "kicker"),
        t(50, 96, title, "title"),
        sub,
    ])


slides = []

slides.append(("slide_01_cover.svg", svg_page(f'''
    <rect x="48" y="82" width="1184" height="520" rx="30" class="card2"/>
    <text x="96" y="160" class="kicker">PARALLEL PROGRAMMING · COROUTINE RESEARCH</text>
    <text x="96" y="238" class="h1">协程：把“等待”</text>
    <text x="96" y="306" class="h1">变便宜的并发抽象</text>
    <text x="100" y="362" class="body2">从线程瓶颈、运行时机制到 Python 实验验证</text>
    <g transform="translate(96 430)">
      {pill(0, 0, 92, "进程", "#334155")}
      <path d="M104 15 L154 15" class="thin" stroke="#64748B"/>
      {pill(166, 0, 92, "线程", "#DC2626")}
      <path d="M270 15 L320 15" class="thin" stroke="#64748B"/>
      {pill(332, 0, 118, "事件循环", "#059669")}
      <path d="M462 15 L512 15" class="thin" stroke="#64748B"/>
      {pill(524, 0, 92, "协程", "#2563EB")}
      <path d="M628 15 L678 15" class="thin" stroke="#64748B"/>
      {pill(690, 0, 118, "虚拟线程", "#7C3AED")}
    </g>
    <rect x="874" y="154" width="274" height="274" rx="137" fill="none" stroke="rgba(255,255,255,0.13)" stroke-width="2"/>
    <path d="M1011 196 C1068 196 1114 242 1114 299 C1114 356 1068 402 1011 402 C954 402 908 356 908 299 C908 242 954 196 1011 196Z" fill="none" stroke="#60A5FA" stroke-width="5"/>
    <path d="M960 302 L1000 342 L1072 258" fill="none" stroke="#34D399" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>
    <text x="1011" y="466" text-anchor="middle" class="body">等待不再独占线程</text>
''', "协程技术调研封面", 1)))

slides.append(("slide_02_problem.svg", svg_page(slide_header("PROBLEM", "高并发服务的主要矛盾是大量等待", "很多请求不是一直在计算，而是在等待网络、数据库、RPC 或定时器。") + f'''
    {card(48, 166, 724, 392, "#2563EB", "card2")}
    <text x="82" y="210" class="kicker">REQUEST LIFECYCLE</text>
    <text x="82" y="246" class="h2">计算很短，等待很长：线程被占住但 CPU 没被充分使用</text>
    <g transform="translate(86 308)">
      <text x="0" y="-18" class="small">一次请求</text>
      <rect x="0" y="0" width="94" height="38" rx="10" fill="#2563EB"/>
      <text x="47" y="25" text-anchor="middle" fill="#fff" font-size="13" font-weight="800">CPU</text>
      <rect x="108" y="0" width="408" height="38" rx="10" fill="rgba(255,255,255,0.12)" stroke="rgba(255,255,255,0.18)"/>
      <text x="312" y="25" text-anchor="middle" class="small">等待 DB / RPC / 网络</text>
      <rect x="530" y="0" width="82" height="38" rx="10" fill="#2563EB"/>
      <text x="571" y="25" text-anchor="middle" fill="#fff" font-size="13" font-weight="800">CPU</text>
      <rect x="0" y="94" width="612" height="1" fill="rgba(255,255,255,0.22)"/>
      <text x="0" y="132" class="body">线程模型：等待期间仍占一个 OS 线程</text>
      <text x="0" y="164" class="body">协程模型：挂起任务，线程继续执行其他可运行任务</text>
    </g>
    {card(792, 166, 440, 182, "#059669")}
    <text x="824" y="208" class="kicker">WAIT SOURCES</text>
    {lines(824, 246, ["网络包到达", "数据库 / Redis / 消息队列", "RPC 下游响应", "定时器、连接池、限流器"], "body", 30)}
    {card(792, 368, 440, 190, "#DC2626")}
    <text x="824" y="410" class="kicker">WHY IT MATTERS</text>
    <text x="824" y="454" class="metric">10K+</text>
    <text x="948" y="444" class="body">连接同时等待时</text>
    <text x="948" y="472" class="body">线程栈、调度和上下文切换会放大成本</text>
    <text x="824" y="518" class="small">核心问题：等待不应成为昂贵的线程占用。</text>
''', "高并发服务的等待问题", 2)))

slides.append(("slide_03_evolution.svg", svg_page(slide_header("EVOLUTION", "并发模型一步步把等待成本降下来", "协程不是凭空出现，而是进程、线程、事件循环之后的抽象折中。") + f'''
    {card(48, 164, 1184, 132, "#2563EB", "card2")}
    <text x="82" y="210" class="h2">演进主线：隔离性、可读性、资源效率之间不断重新平衡</text>
    <text x="82" y="248" class="body">协程把事件驱动的资源效率，重新包装成接近同步代码的表达方式。</text>
    {card(48, 326, 216, 232, "#64748B")}
    <text x="76" y="372" class="h3">进程</text><text x="76" y="410" class="body">隔离强</text><text x="76" y="440" class="small">创建、切换、内存成本高</text>
    {card(284, 326, 216, 232, "#DC2626")}
    <text x="312" y="372" class="h3">线程</text><text x="312" y="410" class="body">代码直观</text><text x="312" y="440" class="small">高并发下线程仍昂贵</text>
    {card(520, 326, 216, 232, "#059669")}
    <text x="548" y="372" class="h3">事件循环</text><text x="548" y="410" class="body">少线程高吞吐</text><text x="548" y="440" class="small">回调链复杂、状态分散</text>
    {card(756, 326, 216, 232, "#2563EB", "card2")}
    <text x="784" y="372" class="h3">协程</text><text x="784" y="410" class="body">顺序代码表达等待</text><text x="784" y="440" class="small">依赖运行时和非阻塞生态</text>
    {card(992, 326, 240, 232, "#7C3AED")}
    <text x="1020" y="372" class="h3">虚拟线程</text><text x="1020" y="410" class="body">接近线程心智</text><text x="1020" y="440" class="small">仍需关注 pinning 与下游容量</text>
''', "并发模型演进", 3)))

slides.append(("slide_04_tradeoff.svg", svg_page(slide_header("ABSTRACTION", "协程把事件驱动性能和顺序代码体验重新组合", "性能不是唯一动因，可维护性同样重要。") + f'''
    {card(48, 166, 360, 392, "#DC2626")}
    <text x="78" y="210" class="kicker">THREAD STYLE</text>
    <text x="78" y="248" class="h2">同步线程式代码</text>
    <text x="78" y="292" class="body">优点：调用链直观</text>
    <text x="78" y="322" class="body">问题：等待也占线程</text>
    <rect x="78" y="370" width="300" height="96" rx="16" fill="rgba(255,255,255,0.08)"/>
    <text x="102" y="405" class="small">data = read()</text>
    <text x="102" y="432" class="small">result = parse(data)</text>
    {card(460, 166, 360, 392, "#059669")}
    <text x="490" y="210" class="kicker">EVENT LOOP</text>
    <text x="490" y="248" class="h2">事件循环回调</text>
    <text x="490" y="292" class="body">优点：少线程高吞吐</text>
    <text x="490" y="322" class="body">问题：状态分散、回调复杂</text>
    <rect x="490" y="370" width="300" height="96" rx="16" fill="rgba(255,255,255,0.08)"/>
    <text x="514" y="405" class="small">read(on_done)</text>
    <text x="514" y="432" class="small">on_done -> parse()</text>
    {card(872, 166, 360, 392, "#2563EB", "card2")}
    <text x="902" y="210" class="kicker">COROUTINE</text>
    <text x="902" y="248" class="h2">async / await 协程</text>
    <text x="902" y="292" class="body">优点：等待省线程</text>
    <text x="902" y="322" class="body">同时保留顺序阅读体验</text>
    <rect x="902" y="370" width="300" height="96" rx="16" fill="rgba(37,99,235,0.22)" stroke="rgba(96,165,250,0.35)"/>
    <text x="926" y="405" class="small">data = await read()</text>
    <text x="926" y="432" class="small">return parse(data)</text>
''', "协程的抽象价值", 4)))

slides.append(("slide_05_definition.svg", svg_page(slide_header("DEFINITION", "协程是可暂停、可恢复的函数", "核心不是并行，而是执行过程可以在挂起点被切开。") + f'''
    {card(48, 166, 720, 392, "#2563EB", "card2")}
    <text x="82" y="210" class="kicker">EXECUTION TRACKS</text>
    <text x="82" y="248" class="h2">普通函数连续执行；协程在 await 点保存现场</text>
    <g transform="translate(94 312)">
      <text x="0" y="0" class="body">普通函数</text>
      <path d="M120 -6 L600 -6" stroke="#94A3B8" stroke-width="8" stroke-linecap="round"/>
      <circle cx="120" cy="-6" r="10" fill="#CBD5E1"/><circle cx="600" cy="-6" r="10" fill="#CBD5E1"/>
      <text x="0" y="84" class="body">协程函数</text>
      <path d="M120 78 L260 78" stroke="#60A5FA" stroke-width="8" stroke-linecap="round"/>
      <path d="M350 78 L490 78" stroke="#60A5FA" stroke-width="8" stroke-linecap="round"/>
      <path d="M560 78 L600 78" stroke="#60A5FA" stroke-width="8" stroke-linecap="round"/>
      <circle cx="260" cy="78" r="12" fill="#2563EB"/><text x="242" y="118" class="small">await I/O</text>
      <circle cx="490" cy="78" r="12" fill="#2563EB"/><text x="466" y="118" class="small">恢复</text>
    </g>
    {card(792, 166, 440, 178, "#059669")}
    <text x="824" y="208" class="kicker">STATE SAVED</text>
    {lines(824, 246, ["局部变量", "下一步执行位置", "返回值与异常", "恢复句柄 / continuation"], "body", 29)}
    {card(792, 364, 440, 194, "#DC2626")}
    <text x="824" y="406" class="kicker">MISCONCEPTION</text>
    <text x="824" y="446" class="h2">协程不是自动并行</text>
    <text x="824" y="482" class="body">它只是让任务在等待时把执行线程交还给调度器。</text>
    <text x="824" y="524" class="small">CPU 密集任务仍需要真正的并行计算资源。</text>
''', "协程定义", 5)))

slides.append(("slide_06_mechanism.svg", svg_page(slide_header("MECHANISM", "协程底层是状态机 + 调度恢复", "编译器或解释器拆分执行过程，运行时在事件完成后恢复任务。") + f'''
    {card(48, 166, 470, 392, "#2563EB")}
    <text x="80" y="208" class="kicker">SOURCE SHAPE</text>
    <rect x="80" y="236" width="392" height="236" rx="16" fill="rgba(15,23,42,0.78)" stroke="rgba(255,255,255,0.16)"/>
    <text x="108" y="280" class="small">async def fetch():</text>
    <text x="108" y="316" class="small">    data = await read()</text>
    <text x="108" y="352" class="small">    return parse(data)</text>
    <text x="80" y="514" class="body">`await` 是显式挂起点：未完成就让出执行权。</text>
    {card(540, 166, 360, 392, "#059669", "card2")}
    <text x="570" y="208" class="kicker">STATE MACHINE</text>
    <g transform="translate(594 248)">
      <rect x="0" y="0" width="252" height="50" rx="14" class="node"/><text x="126" y="32" text-anchor="middle" class="body">State 0: start</text>
      <path d="M126 52 L126 86" class="line" stroke="#64748B"/>
      <rect x="0" y="88" width="252" height="50" rx="14" class="node"/><text x="126" y="120" text-anchor="middle" class="body">State 1: waiting read</text>
      <path d="M126 140 L126 174" class="line" stroke="#64748B"/>
      <rect x="0" y="176" width="252" height="50" rx="14" class="node"/><text x="126" y="208" text-anchor="middle" class="body">State 2: parse return</text>
    </g>
    {card(922, 166, 310, 392, "#DC2626")}
    <text x="950" y="208" class="kicker">WHO DOES WHAT</text>
    {lines(950, 252, ["编译器：生成状态机", "运行时：维护就绪队列", "事件源：通知 I/O 完成", "调度器：恢复协程执行"], "body", 39)}
''', "协程底层机制", 6)))

slides.append(("slide_07_system.svg", svg_page(slide_header("SYSTEM", "OS 调度线程，运行时调度协程", "协程没有绕过操作系统，而是在用户态复用线程。") + f'''
    {card(48, 166, 780, 392, "#2563EB", "card2")}
    <text x="82" y="208" class="kicker">LAYERED ARCHITECTURE</text>
    <g transform="translate(86 248)">
      <rect x="0" y="0" width="680" height="56" rx="16" fill="rgba(37,99,235,0.20)" stroke="rgba(96,165,250,0.35)"/>
      <text x="24" y="36" class="body2">应用代码：async/await · goroutine · virtual thread</text>
      <rect x="0" y="76" width="680" height="56" rx="16" fill="rgba(255,255,255,0.08)" stroke="rgba(255,255,255,0.16)"/>
      <text x="24" y="112" class="body2">语言 / 编译器：协程帧 · 状态机 · continuation</text>
      <rect x="0" y="152" width="680" height="56" rx="16" fill="rgba(5,150,105,0.22)" stroke="rgba(52,211,153,0.35)"/>
      <text x="24" y="188" class="body2">运行时：event loop · scheduler · ready queue</text>
      <rect x="0" y="228" width="680" height="56" rx="16" fill="rgba(220,38,38,0.20)" stroke="rgba(248,113,113,0.35)"/>
      <text x="24" y="264" class="body2">操作系统：OS threads · epoll/kqueue/IOCP · I/O</text>
    </g>
    {card(852, 166, 380, 180, "#059669")}
    <text x="882" y="208" class="kicker">KEY POINT</text>
    <text x="882" y="250" class="h2">协程仍运行在线程上</text>
    <text x="882" y="288" class="body">区别在于等待时不独占线程。</text>
    {card(852, 366, 380, 192, "#64748B")}
    <text x="882" y="408" class="kicker">OS EVENTS</text>
    {lines(882, 446, ["Linux epoll", "BSD / macOS kqueue", "Windows IOCP", "libuv 跨平台封装"], "body", 30)}
''', "系统协同", 7)))

slides.append(("slide_08_languages_a.svg", svg_page(slide_header("LANGUAGES I", "C++、Go、Python 代表三种抽象层级", "同样处理协程/轻量并发，语言给出的工程心智完全不同。") + f'''
    {card(48, 166, 360, 392, "#64748B")}
    <text x="78" y="210" class="kicker">C++20</text>
    <text x="78" y="252" class="h2">底层机制</text>
    {lines(78, 304, ["co_await / co_yield / co_return", "标准提供基础设施", "运行时与调度依赖库实现", "适合高性能系统框架"], "body", 34)}
    {card(460, 166, 360, 392, "#059669", "card2")}
    <text x="490" y="210" class="kicker">GO</text>
    <text x="490" y="252" class="h2">默认并发工具</text>
    {lines(490, 304, ["go f() 启动 goroutine", "runtime 使用 M/P/G 调度", "channel 与 context 组织协作", "适合服务端高并发"], "body", 34)}
    {card(872, 166, 360, 392, "#2563EB")}
    <text x="902" y="210" class="kicker">PYTHON</text>
    <text x="902" y="252" class="h2">显式事件循环</text>
    {lines(902, 304, ["async def / await", "Task 排入 event loop", "TaskGroup 支持结构化并发", "阻塞调用会卡住事件循环"], "body", 34)}
''', "语言对比一", 8)))

slides.append(("slide_09_languages_b.svg", svg_page(slide_header("LANGUAGES II", "现代语言形成两条降低异步复杂度的路线", "显式 async/await 与轻量线程化并存。") + f'''
    {card(48, 166, 520, 392, "#2563EB", "card2")}
    <text x="82" y="210" class="kicker">ROUTE A</text>
    <text x="82" y="252" class="h2">显式 async / await</text>
    <text x="82" y="294" class="body">代表：Python、C#、C++ coroutine 生态</text>
    {lines(82, 342, ["调用链显式异步", "编译器/解释器生成状态机", "适合 I/O API 已异步化的生态", "风险：阻塞调用破坏调度"], "body", 32)}
    {card(608, 166, 624, 392, "#7C3AED")}
    <text x="642" y="210" class="kicker">ROUTE B</text>
    <text x="642" y="252" class="h2">轻量线程化抽象</text>
    <text x="642" y="294" class="body">代表：Go goroutine、Java 21 Virtual Threads</text>
    {lines(642, 342, ["更接近“一任务一执行单元”的心智", "运行时把轻量任务映射到 OS 线程", "传统同步代码迁移成本更低", "边界：CPU密集、pinning、下游容量"], "body", 32)}
''', "语言对比二", 9)))

slides.append(("slide_10_experiment_design.svg", svg_page(slide_header("EXPERIMENT DESIGN", "实验必须同时测 I/O 等待和 CPU 计算", "只测 I/O 会夸大协程适用范围；加入 CPU 场景才能讲清边界。") + f'''
    {card(48, 166, 710, 392, "#2563EB", "card2")}
    <text x="82" y="208" class="kicker">MATRIX</text>
    <rect x="82" y="238" width="636" height="250" rx="18" fill="rgba(255,255,255,0.08)" stroke="rgba(255,255,255,0.16)"/>
    <text x="112" y="282" class="h3">场景</text><text x="260" y="282" class="h3">asyncio</text><text x="430" y="282" class="h3">threads</text><text x="585" y="282" class="h3">指标</text>
    <line x1="104" y1="304" x2="696" y2="304" class="axis"/>
    <text x="112" y="344" class="body">I/O 等待</text><text x="260" y="344" class="small">asyncio.sleep()</text><text x="430" y="344" class="small">time.sleep()</text><text x="585" y="344" class="small">耗时 / 线程</text>
    <line x1="104" y1="372" x2="696" y2="372" class="axis"/>
    <text x="112" y="414" class="body">CPU 计算</text><text x="260" y="414" class="small">coroutine 内循环</text><text x="430" y="414" class="small">线程池循环</text><text x="585" y="414" class="small">耗时 / 吞吐</text>
    <text x="82" y="528" class="small">输出：CSV / JSON / PNG；图表保存在 assets 文件夹。</text>
    {card(788, 166, 444, 176, "#059669")}
    <text x="818" y="208" class="kicker">PARAMETERS</text>
    {lines(818, 246, ["I/O任务数：100 到 10000", "CPU任务数：50、100、200", "重复次数：5", "worker：50、100、200"], "body", 29)}
    {card(788, 362, 444, 196, "#DC2626")}
    <text x="818" y="404" class="kicker">AUDIT FIXES</text>
    {lines(818, 442, ["补 CPU-bound 反例", "补线程峰值采样", "补吞吐字段", "自动输出可用图表"], "body", 29)}
''', "实验设计", 10)))

slides.append(("slide_11_io_result.svg", svg_page(slide_header("I/O RESULT", "I/O 等待中，asyncio 用 1 个主要线程承载 10000 个任务", "协程优势来自等待期间不占线程，而不是让 sleep 本身更快。") + f'''
    {card(48, 166, 760, 392, "#2563EB", "card2")}
    <text x="82" y="208" class="kicker">THREAD PEAK</text>
    <image x="82" y="232" width="690" height="292" preserveAspectRatio="xMidYMid meet" href="../assets/coroutine_exp_io_threads.png"/>
    {card(832, 166, 400, 186, "#059669")}
    <text x="862" y="208" class="kicker">KEY NUMBER</text>
    <text x="862" y="260" class="metric">1 vs 201</text>
    <text x="862" y="296" class="body">asyncio vs threads-200</text>
    <text x="862" y="324" class="small">10000 个 I/O 等待任务</text>
    {card(832, 372, 400, 186, "#64748B")}
    <text x="862" y="414" class="kicker">DURATION</text>
    <text x="862" y="456" class="h2">1.864s vs 2.157s</text>
    <text x="862" y="494" class="body">asyncio 更少线程，同时耗时更低。</text>
    <text x="862" y="526" class="small">threads-50: 2.935s；threads-100: 2.202s</text>
''', "I/O等待实验结果", 11)))

slides.append(("slide_12_cpu_result.svg", svg_page(slide_header("CPU RESULT", "CPU 密集场景下，协程优势消失", "协程擅长调度等待，不负责创造 CPU 算力。") + f'''
    {card(48, 166, 760, 392, "#DC2626", "card2")}
    <text x="82" y="208" class="kicker">CPU-BOUND DURATION</text>
    <image x="82" y="232" width="690" height="292" preserveAspectRatio="xMidYMid meet" href="../assets/coroutine_exp_cpu_duration.png"/>
    {card(832, 166, 400, 180, "#2563EB")}
    <text x="862" y="208" class="kicker">200 TASKS</text>
    <text x="862" y="250" class="h2">耗时基本接近</text>
    <text x="862" y="288" class="body">asyncio: 6.811s</text>
    <text x="862" y="316" class="body">threads-50: 6.696s</text>
    {card(832, 366, 400, 192, "#059669")}
    <text x="862" y="408" class="kicker">TAKEAWAY</text>
    {lines(862, 446, ["CPU任务移出事件循环", "考虑进程池 / 原生扩展", "使用向量化、SIMD 或 GPU", "不要把协程当算力来源"], "body", 29)}
''', "CPU密集实验结果", 12)))

slides.append(("slide_13_engineering.svg", svg_page(slide_header("ENGINEERING RULES", "选择协程前先判断瓶颈", "等待多就用协程；计算多就用并行计算。") + f'''
    {card(48, 166, 560, 392, "#2563EB", "card2")}
    <text x="82" y="208" class="kicker">DECISION TREE</text>
    <g transform="translate(96 250)">
      <rect x="0" y="0" width="460" height="56" rx="16" class="node"/><text x="230" y="36" text-anchor="middle" class="body2">瓶颈是否主要来自 I/O 等待？</text>
      <path d="M230 58 L230 92" class="line" stroke="#64748B"/>
      <rect x="-4" y="96" width="220" height="64" rx="16" fill="rgba(37,99,235,0.24)" stroke="rgba(96,165,250,0.35)"/>
      <text x="106" y="136" text-anchor="middle" class="body">是：协程 / 异步 I/O</text>
      <rect x="244" y="96" width="220" height="64" rx="16" fill="rgba(220,38,38,0.20)" stroke="rgba(248,113,113,0.35)"/>
      <text x="354" y="136" text-anchor="middle" class="body">否：并行计算方案</text>
      <path d="M106 162 L106 196" class="line" stroke="#64748B"/>
      <rect x="-4" y="200" width="220" height="64" rx="16" fill="rgba(5,150,105,0.22)" stroke="rgba(52,211,153,0.35)"/>
      <text x="106" y="240" text-anchor="middle" class="body">加超时、限流、取消</text>
    </g>
    {card(632, 166, 284, 392, "#059669")}
    <text x="662" y="208" class="kicker">USE WHEN</text>
    {lines(662, 250, ["高并发 Web 服务", "RPC / API 聚合", "爬虫与批量请求", "数据库与缓存访问", "长连接与定时器"], "body", 34)}
    {card(948, 166, 284, 392, "#DC2626")}
    <text x="978" y="208" class="kicker">AVOID WHEN</text>
    {lines(978, 250, ["纯 CPU 计算", "大量阻塞库", "强实时调度", "无界任务创建", "缺少下游限流"], "body", 34)}
''', "工程判断", 13)))

slides.append(("slide_14_end.svg", svg_page(f'''
    <rect x="48" y="86" width="1184" height="470" rx="30" class="card2"/>
    <text x="96" y="150" class="kicker">FINAL TAKEAWAY</text>
    <text x="96" y="214" class="h1">会用协程，不是记住一个语法</text>
    <text x="96" y="282" class="h1">而是理解等待如何被重新调度</text>
    <g transform="translate(100 352)">
      {pill(0, 0, 210, "价值：降低等待成本", "#2563EB")}
      {pill(238, 0, 230, "机制：保存状态并恢复", "#059669")}
      {pill(496, 0, 230, "边界：不创造 CPU 算力", "#DC2626")}
    </g>
    <text x="100" y="454" class="body">参考：OpenJDK JEP 444 · Python asyncio · Go Effective Go · Microsoft async/await · C++ coroutines · Linux epoll</text>
    <text x="100" y="494" class="small">AI 使用：用于资料搜集、结构梳理、实验脚本审阅与图表生成辅助；结论依据官方文档和本地实验复核。</text>
''', "总结与展望", 14)))


for name, content in slides:
    (OUT / name).write_text(content, encoding="utf-8")

index_cards = []
for name, _ in slides:
    index_cards.append(f'<section><h2>{escape(name)}</h2><img src="{escape(name)}" alt="{escape(name)}"></section>')

(OUT / "index.html").write_text(
    """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>协程技术调研 SVG Slides</title>
<style>
body{margin:0;background:#0b1020;color:#e5e7eb;font-family:"Microsoft YaHei","Segoe UI",Arial,sans-serif}
main{max-width:1320px;margin:0 auto;padding:28px}
section{margin:0 0 36px}
h1{font-size:28px;margin:0 0 24px}
h2{font-size:16px;color:#94a3b8;font-weight:600}
img{width:100%;border-radius:18px;box-shadow:0 20px 50px rgba(0,0,0,.35);background:#111827}
</style>
</head>
<body><main><h1>协程技术调研 SVG Slides</h1>
"""
    + "\n".join(index_cards)
    + "\n</main></body></html>\n",
    encoding="utf-8",
)

print(f"Generated {len(slides)} SVG slides in {OUT}")
