-- ============================================================
--  高校学科竞赛管理系统  建表脚本（SQLite）
--  说明：和论文里的 E-R 图一一对应，6 张表
-- ============================================================

-- 1. 用户表：学生、教师、管理员都在这张表里，用 role 区分
CREATE TABLE IF NOT EXISTS sys_user (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,          -- 登录账号：学号 / 工号
    password_hash TEXT    NOT NULL,                 -- 密码哈希，不存明文
    real_name     TEXT    NOT NULL,
    role          INTEGER NOT NULL DEFAULT 0,       -- 0=学生 1=教师 2=管理员
    college       TEXT,                             -- 所属学院，统计用
    create_time   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- 2. 竞赛表
CREATE TABLE IF NOT EXISTS competition (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT    NOT NULL,
    level        TEXT    NOT NULL,                  -- 校级 / 省级 / 国家级
    category     TEXT,                              -- 学科类别
    organizer    TEXT,                              -- 主办单位
    sign_start   TEXT    NOT NULL,                  -- 报名开始日期 YYYY-MM-DD
    sign_end     TEXT    NOT NULL,                  -- 报名截止日期
    contest_date TEXT,                              -- 比赛日期
    status       INTEGER NOT NULL DEFAULT 1,        -- 1=报名中 2=报名截止 3=评审中 4=已公示
    description  TEXT,
    create_by    INTEGER REFERENCES sys_user(id),
    create_time  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- 3. 报名记录表
CREATE TABLE IF NOT EXISTS registration (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    competition_id INTEGER NOT NULL REFERENCES competition(id),
    student_id     INTEGER NOT NULL REFERENCES sys_user(id),
    status         INTEGER NOT NULL DEFAULT 0,      -- 0=待审核 1=通过 2=驳回
    reason         TEXT,                            -- 驳回原因
    create_time    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (competition_id, student_id)             -- 同一竞赛同一学生只能报一次
);

-- 4. 成绩表：一个报名对应一条成绩
CREATE TABLE IF NOT EXISTS score (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    registration_id INTEGER NOT NULL UNIQUE REFERENCES registration(id),
    judge_id        INTEGER NOT NULL REFERENCES sys_user(id),
    score           REAL    NOT NULL,               -- 0 ~ 100
    comment         TEXT,
    create_time     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- 5. 获奖表
CREATE TABLE IF NOT EXISTS award (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    registration_id INTEGER NOT NULL UNIQUE REFERENCES registration(id),
    award_level     TEXT    NOT NULL,               -- 一等奖 / 二等奖 / 三等奖
    publish_time    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- 6. 公告表
CREATE TABLE IF NOT EXISTS notice (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    content     TEXT NOT NULL,
    create_by   INTEGER REFERENCES sys_user(id),
    create_time TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
