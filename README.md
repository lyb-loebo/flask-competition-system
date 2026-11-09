# 高校学科竞赛管理系统

Flask + SQLite 实现的教学竞赛管理平台，对应开题报告《基于 Flask 框架的高校学科竞赛管理系统的设计与实现》。

三类角色：**学生**报名竞赛、**教师**审核与打分、**管理员**发布竞赛与公示获奖。

---

## 快速开始 (Quick Start)

请确保本地已安装 Python 3.8+ 环境。在终端中依次执行以下命令：

```bash
# 1. 克隆项目到本地 (或者直接下载 ZIP 解压)
git clone https://github.com/lyb-loebo/flask-competition-system.git

# 2. 进入项目目录
cd flask-competition-system

# 3. 安装依赖包
pip install -r requirements.txt

# 4. 启动 Flask 服务
python app.py

**演示账号**（密码都是 `123456`）：

| 角色 | 账号 |
|---|---|
| 管理员 | `admin` |
| 教师 | `teacher1` |
| 学生 | `2023001` |

> 第一次启动会自动建库 `contest.db` 并写入演示数据。
> 想恢复干净状态：删掉 `contest.db`，重新 `python app.py`。

**验证系统是否正常**：

```powershell
python smoke_test.py
```

最后一行显示「全部通过」就没问题。

---

## 2. 演示脚本
1. `admin` 登录 → 发布竞赛 → 填表提交 → 列表里出现新竞赛
2. 退出，用 `2023005` 登录 → 进竞赛详情 → 点「立即报名」→ 状态变「待审核」
3. 退出，用 `teacher1` 登录 → 待办 → 通过审核 → 给这位学生打分 88
4. 退出，用 `admin` 登录 → 获奖公示 → 给这位学生评「一等奖」
5. 退出，用 `teacher1` 登录 → 待办 → 「已打分」里能看到这条，但提示**已公示不能改**
6. 回到 `admin` 撤销奖项 → 教师再改分/撤销成绩 → 这条报名回到「待打分」

---

## 3. 文件地图

| 文件 | 干什么 |
|---|---|---|
| `app.py` | 路由层：每个函数是一个页面或一次提交 | 第 5 章 系统实现 |
| `db.py` | 数据访问层：所有 SQL 都在这里 | 第 4 章 数据库设计 |
| `schema.sql` | 6 张表的建表语句 | 第 4 章 4.3 表结构 |
| `templates/` | 9 个页面模板 | 第 4 章 界面设计 |
| `static/style.css` | 样式 | 第 4 章 界面设计 |
| `smoke_test.py` | 自检脚本（等价于功能测试） | 第 6 章 系统测试 |
| `contest.db` | SQLite 数据库文件（自动生成） | — |

---

## 4. 数据库设计（6 张表）

```
sys_user        用户（id, 账号, 密码哈希, 姓名, 角色, 学院）
competition     竞赛（id, 名称, 级别, 类别, 主办, 报名起止, 比赛日期, 状态）
registration    报名（id, 竞赛id, 学生id, 状态, 驳回原因）
score           成绩（id, 报名id, 评委id, 分数, 评语）
award           获奖（id, 报名id, 奖项等级）
notice          公告（id, 标题, 内容, 发布人）
```

状态说明：
- 竞赛：1 报名中 / 2 报名截止 / 3 评审中 / 4 已公示
- 报名：0 待审核 / 1 通过 / 2 驳回
- 用户：0 学生 / 1 教师 / 2 管理员

---

## 5. 为什么用 SQLite，MySQL 什么时候上

SQLite 是 Python 自带的，**不用装任何东西**，一个 `.db` 文件就是整个库，备份就是复制文件。

你现在不需要 MySQL。等要换的时候，只需要改 `db.py` 里的两处：

1. `sqlite3.connect(...)` 换成 PyMySQL 或 SQLAlchemy 的连接；
2. `?` 占位符换成 `%s`。

`schema.sql` 里的建表语句基本可以直接用（`INTEGER PRIMARY KEY AUTOINCREMENT` 换成 `BIGINT AUTO_INCREMENT PRIMARY KEY`）。

---

## 8. 常见报错

| 报错 | 原因 | 解决 |
|---|---|---|
| `ModuleNotFoundError: No module named 'flask'` | 没装 Flask | `pip install flask` |
| `OSError: [WinError 10048]` | 5000 端口被占 | 改 `app.py` 最后一行 `port=5001` |
| 页面数据乱了 | 演示数据改坏了 | 删 `contest.db` 重启 |
| 页面 500 | 代码有错 | 看命令行最后一段 Traceback |

`pip install` 慢的话换国内源：

```powershell
pip install flask -i https://pypi.tuna.tsinghua.edu.cn/simple
```
