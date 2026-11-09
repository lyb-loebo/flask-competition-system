# -*- coding: utf-8 -*-
"""自检脚本：不用打开浏览器，一条命令把主要流程跑一遍。

用法（在 contest_system 目录下）：
    python smoke_test.py

看到最后一行是「全部通过」就说明系统是好的。
"""
import os
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import db

# 用临时数据库，不动你真正的 contest.db
db.DB_PATH = os.path.join(tempfile.gettempdir(), "contest_smoke.db")
if os.path.exists(db.DB_PATH):
    os.remove(db.DB_PATH)
db.init_db()
db.seed_data()

import app as app_module  # noqa: E402

app_module.app.config["TESTING"] = True
client = app_module.app.test_client()

fails = []


def check(name, cond, extra=""):
    if cond:
        print("  PASS", name)
    else:
        fails.append(name)
        print("  FAIL", name, extra)


def login(username, password="123456"):
    return client.post("/login", data={"username": username, "password": password})


print("[1] 页面能不能打开")
check("首页 200", client.get("/").status_code == 200)
check("公告页 200", client.get("/notices").status_code == 200)
check("获奖页 200", client.get("/awards").status_code == 200)
check("竞赛详情 200", client.get("/competition/1").status_code == 200)
check("不存在的竞赛 404", client.get("/competition/999").status_code == 404)

print("[2] 登录与权限")
check("错误密码不通过", login("admin", "wrong").status_code == 200)
check("管理员登录成功", login("admin").status_code == 302)
check("登录后首页 200", client.get("/").status_code == 200)
client.get("/logout")
check("未登录访问待办 → 跳登录", client.get("/my").status_code == 302)

print("[3] 学生报名")
check("学生登录", login("2023005").status_code == 302)
check("报名成功", client.post("/competition/1/signup").status_code == 302)
r = client.post("/competition/1/signup", follow_redirects=True)
check("重复报名有提示", "已经报过" in r.get_data(as_text=True))
check("看得到自己的报名状态", "你已报名" in client.get("/competition/1").get_data(as_text=True))
check("学生不能进统计页", client.get("/stats").status_code == 403)
client.get("/logout")

print("[4] 教师审核与打分")
check("教师登录", login("teacher1").status_code == 302)
check("待办页 200", client.get("/my").status_code == 200)

conn = db.get_conn()
pending_id = conn.execute("SELECT id FROM registration WHERE status = 0").fetchone()["id"]
conn.close()
client.post(f"/registration/{pending_id}/audit", data={"action": "pass"})
check("审核通过", db.get_conn().execute(
    "SELECT status FROM registration WHERE id = ?", (pending_id,)).fetchone()["status"] == 1)

conn = db.get_conn()
ungraded_id = conn.execute(
    """SELECT r.id FROM registration r LEFT JOIN score s ON s.registration_id = r.id
       WHERE r.status = 1 AND s.id IS NULL""").fetchone()["id"]
conn.close()
client.post(f"/registration/{ungraded_id}/score", data={"score": "88", "comment": "不错"})
sc = db.get_conn().execute(
    "SELECT score FROM score WHERE registration_id = ?", (ungraded_id,)).fetchone()
check("打分成功", sc is not None and sc["score"] == 88)
check("统计页 200", client.get("/stats").status_code == 200)
client.get("/logout")

print("[5] 管理员发布与公示")
check("管理员登录", login("admin").status_code == 302)
check("发布竞赛页 200", client.get("/competition/new").status_code == 200)
r = client.post("/competition/new", data={
    "title": "自检竞赛", "level": "校级", "category": "测试", "organizer": "教务处",
    "sign_start": "2026-11-01", "sign_end": "2026-12-01",
    "contest_date": "2026-12-20", "status": "1", "description": "自检用",
})
check("发布成功", r.status_code == 302)
check("列表里有新竞赛", "自检竞赛" in client.get("/").get_data(as_text=True))
client.post(f"/awards/{ungraded_id}/publish", data={"level": "一等奖"})
check("获奖公示成功", "一等奖" in client.get("/awards").get_data(as_text=True))

print("[6] 改分、撤销与数据一致性")
client.get("/logout")
check("教师登录", login("teacher1").status_code == 302)
r = client.get("/my")
check("教师能看到已打分列表", "已打分" in r.get_data(as_text=True))

r = client.post(f"/registration/{ungraded_id}/score", data={"score": "91"}, follow_redirects=True)
check("已公示的成绩不能改", "撤销奖项" in r.get_data(as_text=True))
now = db.get_conn().execute(
    "SELECT score FROM score WHERE registration_id = ?", (ungraded_id,)).fetchone()["score"]
check("成绩确实没被改掉", now == 88, now)

client.get("/logout")
check("管理员登录", login("admin").status_code == 302)
client.post(f"/awards/{ungraded_id}/revoke")
n = db.get_conn().execute(
    "SELECT COUNT(*) c FROM award WHERE registration_id = ?", (ungraded_id,)).fetchone()["c"]
check("撤销获奖公示", n == 0)

client.get("/logout")
check("教师登录", login("teacher1").status_code == 302)
r = client.post(f"/registration/{ungraded_id}/score", data={"score": "91"}, follow_redirects=True)
check("撤销获奖后可以改分", "成绩已保存" in r.get_data(as_text=True))

client.post(f"/registration/{ungraded_id}/score/delete")
n = db.get_conn().execute(
    "SELECT COUNT(*) c FROM score WHERE registration_id = ?", (ungraded_id,)).fetchone()["c"]
check("撤销成绩", n == 0)
ungraded_ids = [u["id"] for u in db.list_ungraded()]
check("撤销后回到待打分", ungraded_id in ungraded_ids, ungraded_ids)

print()
if fails:
    print("有 %d 项没通过：" % len(fails))
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("全部通过，可以启动系统了：python app.py")
