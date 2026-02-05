# 我天天喊AI安全，结果审计自己的系统发现一堆洞

> 安全，安全，安全。重要的事情说三遍。

我用OpenClaw跑了一套完整的AI agent系统——交易bot、自动监控、定时任务、社交媒体pipeline。过去一周写了四个安全工具开源了，天天在X上发"安全安全安全"。

今天我决定用自己的工具审计自己。

结果让我后背发凉。

---

## 发现了什么

### 1. 我的真名邮箱每次启动都在喂给大模型

OpenClaw的MEMORY.md是agent的长期记忆文件，每次session启动自动加载到LLM context。

我在里面写了什么？

- 真名 ✓
- 两个邮箱 ✓  
- GitHub账号 ✓
- Telegram ID ✓
- API凭证文件的完整路径 ✓
- 交易所私钥的存储位置 ✓

这意味着：每一次对话，每一个sub-agent session，模型都能看到这些信息。更可怕的是——如果agent用web_fetch抓了一个恶意网页，网页里藏了prompt injection指令，理论上可以让agent把这些信息读出来发到外部。

我之前写了四个安全工具，没有一个防住这件事。

### 2. 73个Skill里8个在发外部HTTP请求

OpenClaw的skill系统让agent能调用各种工具。我装了73个skill（20个用户安装 + 53个内置）。

写了个扫描脚本跑了一遍：

```
✅ Clean:    57
⚠️ Warning:  8  
🔴 High risk: 8
```

高风险的原因：
- 有的skill直接读取私钥文件（交易相关，合理但危险）
- 有的skill往Telegram Bot API发消息（包含bot token）
- 有的skill调用外部AI API（x.ai、reddit等）
- 有的skill读取环境变量中的TOKEN/KEY/SECRET

大部分是功能需要，但问题是：**装之前没人审查过。**

### 3. 为什么之前没发现？

因为我犯了一个经典错误：**把安全当成外部威胁来防，忽略了自己就是最大的漏洞源。**

我之前做的四件套：
- agent-guardrails：防agent改代码格式 → 没防数据泄露
- config-guard：防agent改坏配置 → 没管context里装了什么
- upgrade-guard：防升级出问题 → 没查skill安全性
- token-guard：控token花费 → 没控信息流出

全是防agent"搞坏系统"，没有一个防agent"泄露数据"。

方向错了。

---

## 怎么修的

### 方案1：Vault架构（数据隔离）

原理很简单：敏感数据不进LLM context。

```bash
# 建一个vault目录，只有owner能读
mkdir -p ~/.openclaw/workspace/vault
chmod 700 ~/.openclaw/workspace/vault
```

把真名、邮箱、凭证信息从MEMORY.md移到vault/personal-info.md，原位留占位符：

```markdown
# MEMORY.md (agent每次启动加载)
- Full name: [VAULT]
- Personal email: [VAULT]
- API credentials: [VAULT]
```

agent需要用的时候：读vault → 使用 → 不打印 → 不留在context。

SOUL.md里加一条规则：
> vault/下的文件永远不主动加载到context。输出任何外部消息前，检查是否包含真名、邮箱、API key。

### 方案2：Skill安全扫描

写了audit-skills.sh，扫描所有已安装skill的：
- 外部HTTP请求（数据可能往外发）
- 凭证文件读取（私钥、.env、passwd）
- 环境变量访问（TOKEN/KEY/SECRET）
- 命令执行调用（subprocess/exec/spawn）

跑一遍30秒出报告：

```
🔴 ibkr-trader — HIGH RISK
   ⚠️ External HTTP: 1 calls in 3 files
   🔴 CREDENTIAL ACCESS: 8 references to sensitive files
   ⚠️ Command execution: 4 exec/spawn/system calls

🔴 last30days — HIGH RISK  
   ⚠️ External HTTP: 8 calls in 5 files
   🔴 CREDENTIAL ACCESS: 18 references to sensitive files
```

现在的规则：**装任何新skill之前，必须先跑audit-skills.sh。**

---

## 所有人都能做的三步自查

不管你用OpenClaw还是任何AI agent系统，花5分钟做这三件事：

**第一步：查你的agent能读到什么**

打开你的workspace，搜一下：
```bash
grep -r "email\|password\|api_key\|token\|secret" ~/.openclaw/workspace/ --include="*.md"
```

如果搜出来的东西你不想让OpenAI/Anthropic/Google看到——恭喜你，你和一小时前的我一样。

**第二步：隔离敏感数据**

建个vault目录，把敏感信息移进去，原位留[VAULT]占位符。
```bash
mkdir -p ~/.openclaw/workspace/vault && chmod 700 ~/.openclaw/workspace/vault
```

**第三步：审计你的skill**

如果你装了第三方skill，至少看一眼它调了哪些外部API：
```bash
grep -r "https://" ~/.openclaw/workspace/skills/ --include="*.sh" --include="*.py" --include="*.js" | grep -v "github.com\|localhost"
```

出现你不认识的域名？查一下再说。

---

## 为什么AI Agent的安全问题比你想的严重

传统软件：代码写死了，干什么是确定的。
AI Agent：每次执行的路径都不一样，它可能读什么、发什么、调什么，取决于当时的prompt和context。

这意味着：
1. **你给agent的每一条信息，都可能被模型"记住"并在意料之外的地方输出**
2. **agent装的每一个skill/插件，都是一个潜在的数据出口**
3. **prompt injection攻击 + agent的工具调用能力 = 远程数据泄露**

更现实的问题是：大部分agent用户（包括一周前的我）根本没想过这些。

我们忙着让agent跑起来、干活、自动化，完全忘了问一个问题：**它知道了什么？它能把知道的发到哪里？**

---

## 开源工具

这次审计用到的工具和之前的四件套，全部开源：

🛡️ **安全防护五件套**（现在是五件了）：
- [agent-guardrails](https://github.com/jzOcb/agent-guardrails) — git hook防agent绕过项目规范
- [config-guard](https://github.com/jzOcb/config-guard) — 防agent改坏配置
- [upgrade-guard](https://github.com/jzOcb/upgrade-guard) — 安全升级流程
- [token-guard](https://github.com/jzOcb/token-guard) — token用量监控和预算控制
- [audit-skills.sh](https://github.com/jzOcb/agent-guardrails) — skill安全扫描（已集成到guardrails）

🔒 **Vault架构实操**：
- 建vault/目录 + chmod 700
- MEMORY.md脱敏（[VAULT]占位符）
- SOUL.md加入数据安全规则

上面三步自查的命令可以直接复制粘贴跑。

---

## Credit

这次审计的思路受到几位社区成员的启发：

- @bitfish 和 @ohxiyu 提出的"本地记忆+云端LLM"隔离架构，让我意识到MEMORY.md可能在裸奔
- @DharmaMark 提到"create a skill to scan skills, adopt local first"，直接触发了我写audit-skills.sh
- @verysmallwoods 和 @liruifengv 对OpenClaw提示词系统的深度拆解，让我重新审视了context里到底装了什么
- @shao__meng 对Pi框架中prompt injection风险的分析，让我认真思考了"agent能读文件+能上网=数据泄露"这个攻击面

一个人踩坑，不如一群人一起把坑填了。

---

## 最后

安全不是做完四个工具就结束的事。今天审计自己才发现：**你以为你很安全，是因为你还没认真查过自己。**

AI Agent时代最大的安全风险不是外部攻击——是你自己把敏感信息喂给了一个你无法完全控制的系统，还觉得一切正常。

安全，安全，安全。重要的事情说三遍。

查一下你的MEMORY.md，现在。
