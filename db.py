# -*- coding: utf-8 -*-
"""数据访问层：所有 SQL 都写在这个文件里。

为什么单独拆一个文件？
    和 Java 项目里的 Mapper 是同一个道理——页面/路由只负责接请求，
    数据库操作集中在这里。以后换成 MySQL，只改这个文件的开头几行。
"""
import os
import sqlite3

from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "contest.db")   # 一个文件就是一个数据库


# ---------------------------------------------------------------- 连接与初始化
def get_conn():
    """打开连接。每次请求新建、用完关闭，避免多个请求共用一个连接。"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # 查询结果可以 row["id"] 这样取
    conn.execute("PRAGMA foreign_keys = ON")  # 打开外键约束（SQLite 默认是关的）
    return conn


def init_db():
    """执行 schema.sql 建表。表已经存在时不会重复建。"""
    conn = get_conn()
    with open(os.path.join(BASE_DIR, "schema.sql"), encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


def reset_db():
    """删库重建 + 灌入演示数据。开发时想回到干净状态就跑这个。"""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db()
    seed_data()


def seed_data():
    """第一次启动时写入演示数据，保证打开页面不是空的。"""
    conn = get_conn()
    if conn.execute("SELECT COUNT(*) AS c FROM sys_user").fetchone()["c"] > 0:
        conn.close()
        return

    users = [
        # 用户名       密码      姓名        角色  学院
        ("admin",     "123456", "系统管理员", 2, "教务处"),
        ("teacher1",  "123456", "王老师",    1, "计算机学院"),
        ("teacher2",  "123456", "李老师",    1, "数学学院"),
        ("2023001",   "123456", "张三",      0, "计算机学院"),
        ("2023002",   "123456", "李四",      0, "信息学院"),
        ("2023003",   "123456", "王五",      0, "数学学院"),
        ("2023004",   "123456", "赵六",      0, "计算机学院"),
        ("2023005",   "123456", "孙七",      0, "信息学院"),
    ]
    for username, pwd, name, role, college in users:
        conn.execute(
            """INSERT INTO sys_user (username, password_hash, real_name, role, college)
               VALUES (?, ?, ?, ?, ?)""",
            (username, generate_password_hash(pwd), name, role, college),
        )

    comps = [
        ("全国大学生数学建模竞赛", "国家级", "数学建模", "教务处",
         "2026-10-20", "2026-12-10", "2027-01-15", 1,
         "三人一队完成建模、编程与论文写作，校内选拔后推荐参加国赛。"),
        ("蓝桥杯程序设计大赛", "省级", "程序设计", "计算机学院",
         "2026-10-01", "2026-11-20", "2026-12-20", 1,
         "个人赛，考察算法与编程能力，分 Java、C/C++、Python 三个组别。"),
        ("大学生创新创业训练计划", "校级", "创新创业", "创新创业学院",
         "2026-09-01", "2026-10-15", "2026-11-30", 2,
         "以项目申报形式开展，需提交立项书和中期检查材料。"),
        ("互联网+大学生创新创业大赛", "国家级", "创新创业", "教务处",
         "2026-06-01", "2026-08-31", "2026-10-20", 3,
         "已完成报名，进入校赛评审阶段。"),
    ]
    conn.executemany(
        """INSERT INTO competition
           (title, level, category, organizer, sign_start, sign_end, contest_date, status, description)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        comps,
    )

    def uid(username):
        return conn.execute("SELECT id FROM sys_user WHERE username = ?", (username,)).fetchone()["id"]

    def cid(title):
        return conn.execute("SELECT id FROM competition WHERE title = ?", (title,)).fetchone()["id"]

    # 报名记录：让列表、审核、打分、公示四个页面开机就有数据可看
    regs = [
        (cid("蓝桥杯程序设计大赛"),        uid("2023001"), 1),  # 已通过，待打分
        (cid("全国大学生数学建模竞赛"),    uid("2023002"), 1),  # 已通过，已打分
        (cid("蓝桥杯程序设计大赛"),        uid("2023003"), 0),  # 待审核
        (cid("互联网+大学生创新创业大赛"), uid("2023004"), 1),  # 已通过，待打分
    ]
    conn.executemany(
        "INSERT INTO registration (competition_id, student_id, status) VALUES (?, ?, ?)", regs
    )

    # 给两条报名打上分数
    conn.execute(
        """INSERT INTO score (registration_id, judge_id, score, comment)
           SELECT r.id, ?, 88.5, '算法思路清晰，代码规范'
           FROM registration r
           WHERE r.student_id = ? AND r.competition_id = ?""",
        (uid("teacher1"), uid("2023001"), cid("蓝桥杯程序设计大赛")),
    )
    conn.execute(
        """INSERT INTO score (registration_id, judge_id, score, comment)
           SELECT r.id, ?, 76.0, '模型正确，论文表述可再打磨'
           FROM registration r
           WHERE r.student_id = ? AND r.competition_id = ?""",
        (uid("teacher2"), uid("2023002"), cid("全国大学生数学建模竞赛")),
    )

    # 一条获奖记录
    conn.execute(
        """INSERT INTO award (registration_id, award_level)
           SELECT r.id, '一等奖' FROM registration r
           WHERE r.student_id = ? AND r.competition_id = ?""",
        (uid("2023002"), cid("全国大学生数学建模竞赛")),
    )

    conn.execute(
        "INSERT INTO notice (title, content, create_by) VALUES (?, ?, ?)",
        ("2026 年学科竞赛报名通知", "本学期竞赛报名已开放，请同学们在规定时间内完成报名并关注审核结果。", uid("admin")),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------- 用户
def get_user_by_username(username):
    conn = get_conn()
    row = conn.execute("SELECT * FROM sys_user WHERE username = ?", (username,)).fetchone()
    conn.close()
    return row


def get_user(user_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM sys_user WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return row


# ---------------------------------------------------------------- 竞赛
def list_competitions(status=None, level=None, page=1, size=8):
    """按状态/级别筛选 + 分页。返回 (当前页数据, 总条数)。"""
    conn = get_conn()
    where, args = "WHERE 1 = 1", []
    if status:
        where += " AND status = ?"
        args.append(status)
    if level:
        where += " AND level = ?"
        args.append(level)

    total = conn.execute(f"SELECT COUNT(*) AS c FROM competition {where}", args).fetchone()["c"]
    rows = conn.execute(
        f"SELECT * FROM competition {where} ORDER BY id DESC LIMIT ? OFFSET ?",
        args + [size, (page - 1) * size],
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows], total


def get_competition(comp_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM competition WHERE id = ?", (comp_id,)).fetchone()
    conn.close()
    return row


def create_competition(data):
    conn = get_conn()
    conn.execute(
        """INSERT INTO competition
           (title, level, category, organizer, sign_start, sign_end, contest_date, status, description, create_by)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (data["title"], data["level"], data["category"], data["organizer"],
         data["sign_start"], data["sign_end"], data["contest_date"],
         data["status"], data["description"], data["create_by"]),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------- 报名
def sign_up(comp_id, student_id):
    """报名。靠表上的唯一约束挡住重复报名，不靠“先查再插”。"""
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO registration (competition_id, student_id) VALUES (?, ?)",
            (comp_id, student_id),
        )
        conn.commit()
        return True, "报名成功，等待审核"
    except sqlite3.IntegrityError:
        return False, "你已经报过这个竞赛了"
    finally:
        conn.close()


def get_my_registration(comp_id, student_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM registration WHERE competition_id = ? AND student_id = ?",
        (comp_id, student_id),
    ).fetchone()
    conn.close()
    return row


def list_registrations(comp_id):
    """某个竞赛的报名名单：带学生信息、成绩、获奖，一次查完。"""
    conn = get_conn()
    rows = conn.execute(
        """SELECT r.id, r.status, r.reason, r.create_time,
                  u.real_name, u.username, u.college,
                  s.score, s.comment, a.award_level
           FROM registration r
           JOIN sys_user u     ON u.id = r.student_id
           LEFT JOIN score s   ON s.registration_id = r.id
           LEFT JOIN award a   ON a.registration_id = r.id
           WHERE r.competition_id = ?
           ORDER BY r.id""",
        (comp_id,),
    ).fetchall()
    conn.close()
    return rows


def list_my_registrations(student_id):
    conn = get_conn()
    rows = conn.execute(
        """SELECT r.id, r.status, r.reason, r.create_time,
                  c.id AS competition_id, c.title, c.level, c.contest_date, c.status AS comp_status,
                  s.score, s.comment, a.award_level
           FROM registration r
           JOIN competition c ON c.id = r.competition_id
           LEFT JOIN score s  ON s.registration_id = r.id
           LEFT JOIN award a  ON a.registration_id = r.id
           WHERE r.student_id = ?
           ORDER BY r.id DESC""",
        (student_id,),
    ).fetchall()
    conn.close()
    return rows


def list_pending():
    """待审核的报名（教师/管理员待办）。"""
    conn = get_conn()
    rows = conn.execute(
        """SELECT r.id, r.create_time, u.real_name, u.college,
                  c.id AS competition_id, c.title
           FROM registration r
           JOIN sys_user u    ON u.id = r.student_id
           JOIN competition c ON c.id = r.competition_id
           WHERE r.status = 0
           ORDER BY r.id""",
    ).fetchall()
    conn.close()
    return rows


def list_ungraded():
    """已通过但还没打分的报名（教师待办）。"""
    conn = get_conn()
    rows = conn.execute(
        """SELECT r.id, u.real_name, u.college, c.title
           FROM registration r
           JOIN sys_user u    ON u.id = r.student_id
           JOIN competition c ON c.id = r.competition_id
           LEFT JOIN score s  ON s.registration_id = r.id
           WHERE r.status = 1 AND s.id IS NULL
           ORDER BY r.id""",
    ).fetchall()
    conn.close()
    return rows


def audit(reg_id, status, reason=""):
    conn = get_conn()
    conn.execute(
        "UPDATE registration SET status = ?, reason = ? WHERE id = ?",
        (status, reason, reg_id),
    )
    conn.commit()
    conn.close()


def save_score(reg_id, judge_id, score, comment=""):
    """打分。已有成绩就覆盖（UPSERT），不用先查再判断插还是改。

    已经公示获奖的成绩不允许直接改，必须先撤销奖项，
    否则会出现「一等奖 + 60 分」这种自相矛盾的数据。
    返回 (是否成功, 给用户看的提示)。
    """
    conn = get_conn()
    awarded = conn.execute(
        "SELECT id FROM award WHERE registration_id = ?", (reg_id,)
    ).fetchone()
    if awarded:
        conn.close()
        return False, "该成绩已公示获奖，不能修改，请先在获奖公示页撤销奖项"

    conn.execute(
        """INSERT INTO score (registration_id, judge_id, score, comment)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(registration_id) DO UPDATE SET
               score = excluded.score,
               comment = excluded.comment,
               judge_id = excluded.judge_id""",
        (reg_id, judge_id, score, comment),
    )
    conn.commit()
    conn.close()
    return True, "成绩已保存"


def delete_score(reg_id):
    """撤销成绩。撤销后这条报名会重新回到「待打分」列表。"""
    conn = get_conn()
    awarded = conn.execute(
        "SELECT id FROM award WHERE registration_id = ?", (reg_id,)
    ).fetchone()
    if awarded:
        conn.close()
        return False, "该成绩已公示获奖，不能撤销，请先在获奖公示页撤销奖项"

    conn.execute("DELETE FROM score WHERE registration_id = ?", (reg_id,))
    conn.commit()
    conn.close()
    return True, "成绩已撤销，可以重新打分"


def list_scored_registrations():
    """已经打过分的报名（教师改分、撤销用）。award_id 不为空说明已公示。"""
    conn = get_conn()
    rows = conn.execute(
        """SELECT r.id, u.real_name, u.college, c.title,
                  s.score, s.comment, a.id AS award_id, a.award_level
           FROM registration r
           JOIN sys_user u    ON u.id = r.student_id
           JOIN competition c ON c.id = r.competition_id
           JOIN score s       ON s.registration_id = r.id
           LEFT JOIN award a  ON a.registration_id = r.id
           ORDER BY r.id""",
    ).fetchall()
    conn.close()
    return rows


# ---------------------------------------------------------------- 获奖与公告
def publish_award(reg_id, level):
    conn = get_conn()
    conn.execute(
        """INSERT INTO award (registration_id, award_level) VALUES (?, ?)
           ON CONFLICT(registration_id) DO UPDATE SET award_level = excluded.award_level""",
        (reg_id, level),
    )
    conn.commit()
    conn.close()


def list_awards():
    conn = get_conn()
    rows = conn.execute(
        """SELECT a.id, a.registration_id, a.award_level, a.publish_time,
                  u.real_name, u.college, c.title
           FROM award a
           JOIN registration r ON r.id = a.registration_id
           JOIN sys_user u     ON u.id = r.student_id
           JOIN competition c  ON c.id = r.competition_id
           ORDER BY a.id DESC""",
    ).fetchall()
    conn.close()
    return rows


def revoke_award(reg_id):
    """撤销获奖公示。撤销后成绩解锁，可以重新改分或撤销成绩。"""
    conn = get_conn()
    conn.execute("DELETE FROM award WHERE registration_id = ?", (reg_id,))
    conn.commit()
    conn.close()


def list_scored():
    """已打分、可评奖的报名（管理员用）。"""
    conn = get_conn()
    rows = conn.execute(
        """SELECT r.id, u.real_name, c.title, s.score, a.award_level
           FROM registration r
           JOIN sys_user u    ON u.id = r.student_id
           JOIN competition c ON c.id = r.competition_id
           JOIN score s       ON s.registration_id = r.id
           LEFT JOIN award a  ON a.registration_id = r.id
           ORDER BY s.score DESC""",
    ).fetchall()
    conn.close()
    return rows


def list_notices():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM notice ORDER BY id DESC").fetchall()
    conn.close()
    return rows


def add_notice(title, content, user_id):
    conn = get_conn()
    conn.execute(
        "INSERT INTO notice (title, content, create_by) VALUES (?, ?, ?)",
        (title, content, user_id),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------- 统计
def stats_by_college():
    conn = get_conn()
    rows = conn.execute(
        """SELECT u.college AS name, COUNT(*) AS value
           FROM registration r
           JOIN sys_user u ON u.id = r.student_id
           GROUP BY u.college
           ORDER BY value DESC""",
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def stats_by_award():
    conn = get_conn()
    rows = conn.execute(
        "SELECT award_level AS name, COUNT(*) AS value FROM award GROUP BY award_level",
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def stats_by_status():
    conn = get_conn()
    rows = conn.execute(
        "SELECT status AS name, COUNT(*) AS value FROM competition GROUP BY status",
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
