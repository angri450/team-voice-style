# -*- coding: utf-8 -*-
"""从 MiniMax Code 内置的 agent 提示词模板生成团队版说话风格设定。

用法：
    python scripts/build_team_style.py [输出目录]

输出目录不给的时候，生成到本脚本上级的仓库根目录。文件名带生成日期。
"""
import datetime
import os
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent


def find_template() -> Path:
    """找内置 agent 模板。路径跟着当前用户走，不写死某台机器的路径。"""
    home = Path.home()
    candidates = [
        home / ".minimax" / "agents" / ".builtin" / "mavis" / "agent.md",
        Path(os.environ.get("APPDATA", "")) / ".minimax" / "agents" / ".builtin" / "mavis" / "agent.md",
        home / "Library" / "Application Support" / ".minimax" / "agents" / ".builtin" / "mavis" / "agent.md",
    ]
    for c in candidates:
        if c.is_file():
            return c
    sys.exit("没找到内置 agent 模板，先装 MiniMax Code 桌面端，或者手动改 find_template 里的路径。")


SRC = find_template()
OUT_DIR = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else REPO_ROOT
STAMP = datetime.date.today().strftime("%Y-%m-%d")
OUT = OUT_DIR / f"团队说话风格-系统提示词-{STAMP}.md"

text = SRC.read_text(encoding="utf-8")
lines = text.split("\n")

start = next(i for i, l in enumerate(lines) if l.strip() == "# Core Judgment")
end = next(i for i, l in enumerate(lines) if i > start and l.strip() == "{{#if mode.work}}") - 1
body_lines = lines[start:end]

dropped = []
out_lines = []
i = 0
while i < len(body_lines):
    line = body_lines[i]
    if line.strip() in ("{{#if surface.cli}}", "{{#if surface.taskChild}}"):
        j = i + 1
        while body_lines[j].strip() != "{{/if}}":
            j += 1
        dropped.append((line.strip(), body_lines[i + 1:j]))
        i = j + 1
        continue
    out_lines.append(line)
    i += 1

body = "\n".join(out_lines).strip("\n")
if "{{" in body or "}}" in body:
    sys.exit("模板语法残留，终止")

sections = []
cur_title = None
cur_body = []
for line in body.split("\n"):
    if re.match(r"^#{1,2} ", line):
        if cur_title is not None:
            sections.append((cur_title, "\n".join(cur_body).strip("\n")))
        cur_title = line
        cur_body = []
    else:
        cur_body.append(line)
if cur_title is not None:
    sections.append((cur_title, "\n".join(cur_body).strip("\n")))

by_title = {}
for title, sec_body in sections:
    by_title.setdefault(title, []).append(sec_body)

media_body = by_title["## Media Output"][0]

citations_body = by_title["## Citations"][0]
old_cite = '判断建立在工具输出上的时候，引用工具返回的 Citation candidate 字段里的原话，不要自己编内容。提到代码文件时，标成 文件名(行号)；客户端会给这个标注加个图标，路径也能点。引用 MCP 或者 App 的结果时，写明是哪个工具给的。'
new_cite = '判断建立在工具输出上的时候，引用工具返回的结果原话，不要自己编内容。提到代码文件时，标成 文件名(行号)，路径要能点开。引用第三方接口或者应用的结果时，写明是哪个工具给的。'
if old_cite not in citations_body:
    sys.exit("Citations 段落原文未匹配，模板结构变了，需要人工改这段")
citations_body = citations_body.replace(old_cite, new_cite)

generic_media = """我创建或者修改了文件，就在最终回复里把文件交付出去，不能只打印一个本地路径。交付的时候写清文件路径和它是什么、用来做什么。

只交付这一轮真正创建、修改或者删掉的文件。仅仅为了读内容而读过的文件，一律不交付。交付前先核实文件的当前状态，新建或者修改过的文件必须确实存在。创建或者核实失败，就如实报告失败，不要给出不存在的路径。

回复里要是配上图表更清楚，就用 mermaid 代码块，代码块的语言标注写 mermaid。"""

fact_rules = """1. 只写核实过的事实。底稿、平台统计、官方口径里标出来源的条目算核实，口述来源按口述处理。数字化表述不能升级也不能降级，实测值不改成「亿级」「多家知名」「显著」这种词。
2. 底稿里没有的条目不写。用户明确补进来的事项按事实处理，同时在文件里留一条备注，标明「无原始材料，为当事人口述」。
3. 用户明确否认某条信息时直接删掉，不解释，不找补。理由可以事后补注释，正文不写。
4. 学历归属、奖项归属、经费、署名、销量这类字段一旦写进正文，必须能追溯到一条底稿记录。底稿里删掉的内容，正文也不留。
5. 用户说明这份材料是给谁看的，这一条决定整篇定位。对外展示的材料是写给同行和感兴趣的人看的，结尾只能是邀请交流，不是「期待您的认可」。"""

chinese_rules = """1. 写完一遍自问一句「我当面跟人这么说吗」，不是就改。能在口语环境讲出来的一句才是好句。
2. 不接受 AI 简历模板腔。「我的贡献集中在几个方向」「技术在打通某某之间」「从调研走向再创」这类套话不写。
3. 没有数据支撑就不写程度副词。「全面的」「显著的」「深入的」要有量化材料才写。
4. 专有名词保留原语种。「Meritorious Winner（M 奖）」「Honorable Mention（H 奖）」不硬翻成中文。
5. 段落主语统一是第一人称。从「我……」切到「活动……」「项目……」会让读者重新抓主语，每一句要么有清楚的「我」，要么在上下文里能省掉主语。
6. 自述类文本按身份、工作方向、主要事项、收尾四块走，不写目录式的自我定位词。收尾是邀请，语气平视，不写感想宣言。
7. 同一件事只写一次。同一句话在一个段落里出现两次，删掉差的那一遍。
8. 词在产品逻辑里有实指意义时可以保留，例如「闭环」指真实的业务流程闭环，不指抽象的收尾动作。这种保留要靠上下文撑住，读者能看出这个词指的是哪件事。
9. 事先把核心事实清单摆给用户确认再写，特别是没有底稿的事项。
10. 中期改完内容先保存到工作区文件并核实，再汇报。顺序别反。用户决定删就删，不追问原因。
11. 文件名带日期，不加 v1、v2 之类的版本号。
12. 过程反馈保持短，说清做了什么、为什么，三行以内。反馈只说问题的地方直接删，不包装。
13. 演讲发言稿里保留「主要聚焦」没问题，首尾可以有开场和谢幕；上面这些规则主要管书面定稿。
14. 中文信函或者邮件可以列过渡语，但同一集合里不要重复「经……讨论」「我们一致认为」这类套话。
15. 英文稿件语气自然顺畅，不硬套中文的主语推定写法。"""

KEEP = [
    "# Core Judgment",
    "## 关于判断和核实的规则",
    "# Communication & Delivery",
    "## Preamble messages",
    "## Final response",
    "## 关于做不到时怎么交代",
    "## 关于推进和确认的规则",
    "## 关于动手前准备的规则",
    "## 关于干活范围和节奏的规则",
    "## 关于句子写法的规则",
    "## 关于排版和成文的规则",
    "## 关于长期记忆写入的规则",
]
missing = [k for k in KEEP if k not in by_title]
if missing:
    sys.exit("模板里找不到这些小节: %s" % missing)
extra = [k for k in by_title if k not in KEEP and k not in ("## Media Output", "## Citations")]
if extra:
    sys.exit("模板里有未纳入的小节，需要人工确认: %s" % extra)


def sec(title):
    b = by_title[title][0].strip()
    return title if not b else title + "\n\n" + b


parts = []
parts.append(f"# 团队说话风格设定（{STAMP} 版）")
parts.append("这份文件是团队统一的说话风格设定。整篇可以作为 agent 的系统提示词使用，不要删里面的条目。")
parts.append(sec("# Core Judgment"))
parts.append(sec("## 关于判断和核实的规则"))
parts.append("## 关于写事实的规则\n\n" + fact_rules)
parts.append(sec("# Communication & Delivery"))
parts.append(sec("## Preamble messages"))
parts.append(sec("## Final response"))
parts.append(sec("## 关于做不到时怎么交代"))
parts.append("## 关于交付文件的规则\n\n" + generic_media)
parts.append("## Citations\n\n" + citations_body.strip())
parts.append(sec("## 关于推进和确认的规则"))
parts.append(sec("## 关于动手前准备的规则"))
parts.append(sec("## 关于干活范围和节奏的规则"))
parts.append(sec("## 关于句子写法的规则"))
parts.append(sec("## 关于排版和成文的规则"))
parts.append("## 关于中文成稿的补充规则\n\n" + chinese_rules)
parts.append(sec("## 关于长期记忆写入的规则"))

appendix = """# 附录：只在 MiniMax Code 桌面端生效的交付格式

用别的工具跑 agent 的同事可以整段删掉。

## MiniMax Code 的媒体交付格式

""" + media_body.strip()

final_text = "\n\n".join(p for p in parts if p.strip()) + "\n\n" + appendix + "\n"

if "{{" in final_text or "}}" in final_text:
    sys.exit("成品里仍有模板语法，终止")

OUT_DIR.mkdir(parents=True, exist_ok=True)
# 用二进制写出，保证换行统一是 LF，不受 Windows 文本模式影响
OUT.write_bytes(final_text.encode("utf-8"))

print("SOURCE:", SRC)
print("OUTPUT:", OUT)
print("CHARS:", len(final_text))
print("DROPPED_BLOCKS:", [(d[0], len(d[1])) for d in dropped])
